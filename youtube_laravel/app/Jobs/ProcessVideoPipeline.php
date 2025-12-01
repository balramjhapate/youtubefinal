<?php

namespace App\Jobs;

use App\Models\VideoDownload;
use App\Services\VideoDownloadService;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;

class ProcessVideoPipeline implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public function __construct(
        public int $videoId
    ) {}

    public function handle(
        VideoDownloadService $videoDownloadService
    ): void {
        $video = VideoDownload::findOrFail($this->videoId);

        // Update pipeline status
        $video->update([
            'processing_v2_status' => 'running',
            'processing_v2_started_at' => now(),
        ]);

        try {
            // Step 1: Download Video
            $video->update([
                'step_download_status' => 'processing',
                'processing_v2_current_step' => 'Downloading video',
            ]);

            if (! $video->is_downloaded && $video->video_url) {
                $filename = ($video->video_id ?? 'video').'_'.$video->id.'.mp4';
                $path = $videoDownloadService->download($video->video_url, $filename);

                if ($path) {
                    $video->update([
                        'local_file' => $path,
                        'is_downloaded' => true,
                        'step_download_status' => 'completed',
                    ]);
                } else {
                    $video->update([
                        'step_download_status' => 'failed',
                        'processing_v2_status' => 'failed',
                        'error_message' => 'Video download failed',
                    ]);

                    return;
                }
            } else {
                $video->update(['step_download_status' => 'completed']);
            }

            // Step 2: Dispatch Transcription Job
            $video->update([
                'processing_v2_current_step' => 'Starting transcription',
            ]);
            TranscribeVideoJob::dispatch($video->id, true); // Extract frames for visual analysis

            // Step 3: Wait for transcription to complete (or dispatch AI processing after transcription)
            // Note: In a real pipeline, you might want to chain jobs or use job events
            // For now, we'll let individual jobs handle their own status updates

            $video->update([
                'processing_v2_status' => 'in_progress',
                'processing_v2_current_step' => 'Pipeline started - jobs dispatched',
            ]);
        } catch (\Exception $e) {
            $video->update([
                'processing_v2_status' => 'failed',
                'error_message' => 'Pipeline error: '.$e->getMessage(),
            ]);
        }
    }
}
