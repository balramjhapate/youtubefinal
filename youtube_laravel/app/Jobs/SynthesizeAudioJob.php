<?php

namespace App\Jobs;

use App\Models\VideoDownload;
use App\Services\GoogleTTSService;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;

class SynthesizeAudioJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public function __construct(
        public int $videoId,
        public string $languageCode = 'hi-IN',
        public string $voiceName = 'hi-IN-Standard-A'
    ) {}

    public function handle(GoogleTTSService $ttsService): void
    {
        $video = VideoDownload::findOrFail($this->videoId);

        // Check if clean script exists
        if (! $video->transcript_clean_script) {
            $video->update([
                'step_tts_synthesis_status' => 'failed',
                'synthesis_error' => 'Clean script not found. Please generate script first.',
            ]);

            return;
        }

        $video->update([
            'step_tts_synthesis_status' => 'processing',
        ]);

        // Generate output path
        $filename = 'synthesized_audio/tts_'.($video->video_id ?? $video->id).'_'.time().'.mp3';
        $outputPath = $filename;

        // Synthesize audio
        $success = $ttsService->synthesize(
            $video->transcript_clean_script,
            $this->languageCode,
            $this->voiceName,
            $outputPath,
            $video->duration // Target duration to match video
        );

        if ($success) {
            $video->update([
                'step_tts_synthesis_status' => 'completed',
                'synthesized_audio_path' => $outputPath,
                'synthesized_at' => now(),
            ]);
        } else {
            $video->update([
                'step_tts_synthesis_status' => 'failed',
                'synthesis_error' => 'TTS synthesis failed',
            ]);
        }
    }
}
