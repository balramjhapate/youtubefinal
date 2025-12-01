<?php

namespace App\Jobs;

use App\Models\VideoDownload;
use App\Services\AIOptimizationService;
use App\Services\ScriptGenerationService;
use App\Services\TranscriptionService;
use App\Services\TranslationService;
use App\Services\VisualAnalysisService;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;

class TranscribeVideoJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public function __construct(
        public int $videoId,
        public bool $extractFrames = false
    ) {}

    public function handle(
        TranscriptionService $transcriptionService,
        VisualAnalysisService $visualAnalysisService,
        AIOptimizationService $aiOptimizationService,
        ScriptGenerationService $scriptGenerationService,
        TranslationService $translationService
    ): void {
        $video = VideoDownload::findOrFail($this->videoId);

        $video->update([
            'transcription_status' => 'transcribing',
            'transcript_started_at' => now(),
        ]);

        // Step 1: Transcribe (with optional frame extraction)
        $result = $transcriptionService->transcribe($video, $this->extractFrames);

        if ($result['status'] !== 'success') {
            $video->update([
                'transcription_status' => 'failed',
                'transcript_error_message' => $result['error'] ?? 'Transcription failed',
            ]);

            return;
        }

        $originalTranscript = $result['text'];
        $optimizedTranscript = $originalTranscript;
        $cleanScript = $originalTranscript;

        // Step 2: Visual Analysis (if frames extracted)
        $visualAnalysis = null;
        if (! empty($result['visual_frames'])) {
            $visualAnalysis = $visualAnalysisService->analyzeFrames(
                $result['visual_frames'],
                $originalTranscript
            );
        }

        // Step 3: AI Optimization (compare transcript + visual data)
        if ($visualAnalysis) {
            $optimizationResult = $aiOptimizationService->optimizeTranscript(
                $originalTranscript,
                $visualAnalysis
            );
            if ($optimizationResult['status'] === 'success') {
                $optimizedTranscript = $optimizationResult['optimized_transcript'];
            }
        }

        // Step 4: Generate clean script for TTS
        $scriptResult = $scriptGenerationService->generateCleanScript($optimizedTranscript, 'hi');
        if ($scriptResult['status'] === 'success') {
            $cleanScript = $scriptResult['clean_script'];
        }

        // Step 5: Save all results
        $video->update([
            'transcription_status' => 'transcribed',
            'transcript' => $originalTranscript,
            'transcript_optimized' => $optimizedTranscript,
            'transcript_clean_script' => $cleanScript,
            'transcript_language' => $result['language'],
            'transcript_processed_at' => now(),
            'transcript_hindi' => $translationService->translate($cleanScript, 'hi'),
            'visual_analysis' => $visualAnalysis ? json_encode($visualAnalysis) : null,
        ]);
    }
}
