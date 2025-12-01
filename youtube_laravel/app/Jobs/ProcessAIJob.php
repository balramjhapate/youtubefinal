<?php

namespace App\Jobs;

use App\Models\VideoDownload;
use App\Services\AIService;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;

class ProcessAIJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public function __construct(
        public int $videoId
    ) {}

    public function handle(AIService $aiService): void
    {
        $video = VideoDownload::findOrFail($this->videoId);

        $video->update(['ai_processing_status' => 'processing']);

        $result = $aiService->processVideo($video);

        if ($result['status'] === 'success') {
            $video->update([
                'ai_processing_status' => 'processed',
                'ai_summary' => $result['summary'],
                'ai_tags' => implode(',', $result['tags']),
                'ai_processed_at' => now(),
            ]);
        } else {
            $video->update([
                'ai_processing_status' => 'failed',
                'ai_error_message' => $result['error'] ?? 'AI processing failed',
            ]);
        }
    }
}
