<?php

namespace App\Jobs;

use App\Models\VideoDownload;
use App\Services\VideoProcessingService;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;

class ProcessFinalVideoJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public function __construct(
        public int $videoId,
        public ?string $watermarkPath = null
    ) {}

    public function handle(VideoProcessingService $videoProcessingService): void
    {
        $video = VideoDownload::findOrFail($this->videoId);

        // Check prerequisites
        if (! $video->local_file) {
            $video->update([
                'step_final_video_status' => 'failed',
            ]);

            return;
        }

        if (! $video->synthesized_audio_path) {
            $video->update([
                'step_final_video_status' => 'failed',
            ]);

            return;
        }

        $video->update([
            'step_final_video_status' => 'processing',
        ]);

        // Process final video
        $processedVideoPath = $videoProcessingService->processFinalVideo($video, $this->watermarkPath);

        if ($processedVideoPath) {
            $video->update([
                'step_final_video_status' => 'completed',
                'final_video_path' => $processedVideoPath,
            ]);
        } else {
            $video->update([
                'step_final_video_status' => 'failed',
            ]);
        }
    }
}
