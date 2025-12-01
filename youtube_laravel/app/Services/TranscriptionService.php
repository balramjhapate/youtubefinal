<?php

namespace App\Services;

use App\Models\VideoDownload;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Storage;

class TranscriptionService
{
    private string $ncaApiUrl;

    private string $ncaApiKey;

    private bool $ncaEnabled;

    private ?string $openaiApiKey;

    private bool $openaiEnabled;

    public function __construct()
    {
        $this->ncaApiUrl = config('services.nca.api_url');
        $this->ncaApiKey = config('services.nca.api_key');
        $this->ncaEnabled = config('services.nca.enabled', false);
        $this->openaiApiKey = config('services.openai.api_key');
        $this->openaiEnabled = ! empty($this->openaiApiKey);
    }

    /**
     * Transcribe video using Whisper or NCA API
     * Optionally extract visual frames for analysis
     */
    public function transcribe(VideoDownload $video, bool $extractFrames = false): array
    {
        if (! $video->local_file || ! Storage::disk('public')->exists($video->local_file)) {
            return [
                'status' => 'error',
                'error' => 'Video file not found',
            ];
        }

        $transcriptResult = null;
        $visualFrames = null;

        // Step 1: Try NCA API first (faster)
        if ($this->ncaEnabled) {
            $transcriptResult = $this->transcribeViaNCA($video);
        }

        // Step 2: Try OpenAI Whisper API if NCA fails
        if ((! $transcriptResult || $transcriptResult['status'] !== 'success') && $this->openaiEnabled) {
            $transcriptResult = $this->transcribeViaOpenAIWhisper($video);
        }

        // Step 3: Fallback to local Whisper if APIs fail
        if (! $transcriptResult || $transcriptResult['status'] !== 'success') {
            $transcriptResult = $this->transcribeViaWhisper($video);
        }

        // Step 3: Extract visual frames (optional)
        if ($extractFrames && $transcriptResult['status'] === 'success') {
            $visualFrames = $this->extractVisualFrames($video);
        }

        return [
            'status' => $transcriptResult['status'],
            'text' => $transcriptResult['text'] ?? '',
            'language' => $transcriptResult['language'] ?? 'auto',
            'visual_frames' => $visualFrames, // Optional: frame analysis data
        ];
    }

    private function transcribeViaNCA(VideoDownload $video): array
    {
        try {
            $filePath = Storage::disk('public')->path($video->local_file);

            $response = Http::timeout(600)
                ->withHeaders([
                    'Authorization' => 'Bearer '.$this->ncaApiKey,
                ])
                ->attach('file', file_get_contents($filePath), basename($filePath))
                ->post($this->ncaApiUrl.'/v1/toolkit/transcribe');

            if ($response->successful()) {
                $data = $response->json();

                return [
                    'status' => 'success',
                    'text' => $data['transcript'] ?? '',
                    'language' => $data['language'] ?? 'auto',
                ];
            }
        } catch (\Exception $e) {
            Log::error('NCA transcription error: '.$e->getMessage());
        }

        return ['status' => 'error', 'error' => 'NCA API failed'];
    }

    private function transcribeViaWhisper(VideoDownload $video): array
    {
        try {
            // Option 1: Use local Whisper installation
            $filePath = Storage::disk('public')->path($video->local_file);

            // Run Whisper command (requires Whisper installed)
            $command = 'whisper "'.$filePath.'" --language auto --output_format txt --output_dir '.storage_path('app/temp');
            exec($command, $output, $returnCode);

            if ($returnCode === 0) {
                $txtFile = storage_path('app/temp/'.basename($filePath, '.mp4').'.txt');
                if (file_exists($txtFile)) {
                    $text = file_get_contents($txtFile);
                    unlink($txtFile); // Clean up

                    return [
                        'status' => 'success',
                        'text' => $text,
                        'language' => 'auto', // Whisper detects automatically
                    ];
                }
            }

        } catch (\Exception $e) {
            Log::error('Whisper transcription error: '.$e->getMessage());
        }

        return [
            'status' => 'error',
            'error' => 'Whisper transcription failed',
        ];
    }

    private function transcribeViaOpenAIWhisper(VideoDownload $video): array
    {
        try {
            $filePath = Storage::disk('public')->path($video->local_file);
            $model = config('services.openai.whisper.model', 'whisper-1');

            // Use OpenAI PHP SDK
            $client = \OpenAI::client($this->openaiApiKey);
            $response = $client->audio()->transcriptions()->create([
                'model' => $model,
                'file' => fopen($filePath, 'r'),
                'response_format' => 'text',
            ]);

            return [
                'status' => 'success',
                'text' => $response,
                'language' => 'auto', // OpenAI Whisper detects automatically
            ];
        } catch (\Exception $e) {
            Log::error('OpenAI Whisper transcription error: '.$e->getMessage());

            return [
                'status' => 'error',
                'error' => 'OpenAI Whisper API failed: '.$e->getMessage(),
            ];
        }
    }

    /**
     * Extract visual frames from video for analysis (optional)
     */
    private function extractVisualFrames(VideoDownload $video): ?array
    {
        try {
            $filePath = Storage::disk('public')->path($video->local_file);

            // Use ffmpeg to extract frames at intervals
            // Extract 1 frame per 5 seconds
            $outputDir = storage_path('app/temp/frames_'.$video->id);
            if (! is_dir($outputDir)) {
                mkdir($outputDir, 0755, true);
            }

            $command = sprintf(
                'ffmpeg -i "%s" -vf "fps=1/5" "%s/frame_%%03d.jpg" -y',
                $filePath,
                $outputDir
            );

            exec($command, $output, $returnCode);

            if ($returnCode === 0) {
                $frames = [];
                $frameFiles = glob($outputDir.'/frame_*.jpg');

                foreach ($frameFiles as $frameFile) {
                    // Optionally analyze frame with vision AI
                    $frames[] = [
                        'path' => $frameFile,
                        'timestamp' => $this->extractTimestampFromFilename($frameFile),
                        // 'analysis' => $this->analyzeFrame($frameFile), // Optional: AI vision analysis
                    ];
                }

                return $frames;
            }
        } catch (\Exception $e) {
            Log::error('Frame extraction error: '.$e->getMessage());
        }

        return null;
    }

    private function extractTimestampFromFilename(string $filename): float
    {
        // Extract timestamp from frame filename
        // frame_001.jpg = 5 seconds, frame_002.jpg = 10 seconds, etc.
        if (preg_match('/frame_(\d+)\.jpg/', $filename, $matches)) {
            return (int) $matches[1] * 5; // 5 seconds per frame
        }

        return 0;
    }
}
