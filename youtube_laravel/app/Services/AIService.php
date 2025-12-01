<?php

namespace App\Services;

use App\Models\VideoDownload;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class AIService
{
    public function processVideo(VideoDownload $video): array
    {
        $apiKey = config('services.gemini.api_key');
        if (! $apiKey) {
            return [
                'status' => 'error',
                'error' => 'Gemini API key not configured',
            ];
        }

        return $this->processWithGemini($video, $apiKey);
    }

    private function processWithGemini(VideoDownload $video, string $apiKey): array
    {
        try {
            $prompt = $this->buildPrompt($video);

            $response = Http::timeout(60)
                ->withHeaders([
                    'Content-Type' => 'application/json',
                ])
                ->post("https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={$apiKey}", [
                    'contents' => [
                        [
                            'parts' => [
                                ['text' => $prompt],
                            ],
                        ],
                    ],
                ]);

            if ($response->successful()) {
                $data = $response->json();
                $text = $data['candidates'][0]['content']['parts'][0]['text'] ?? '';

                return $this->parseAIResponse($text);
            }
        } catch (\Exception $e) {
            Log::error('Gemini AI error: '.$e->getMessage());
        }

        return [
            'status' => 'error',
            'error' => 'AI processing failed',
        ];
    }

    private function buildPrompt(VideoDownload $video): string
    {
        $transcript = $video->transcript_optimized ?? $video->transcript ?? 'No transcript available';
        $visualContext = '';

        // Include visual analysis if available
        if ($video->visual_analysis) {
            $visualData = json_decode($video->visual_analysis, true);
            if ($visualData) {
                $visualContext = "\n\nVisual Context from Video Frames:\n";
                foreach ($visualData as $analysis) {
                    $visualContext .= sprintf(
                        "[%ds] %s - Objects: %s\n",
                        $analysis['timestamp'] ?? 0,
                        $analysis['description'] ?? '',
                        implode(', ', $analysis['objects'] ?? [])
                    );
                }
            }
        }

        return "Analyze this video transcript and visual context to provide:\n\n".
               "1. A concise summary (2-3 sentences) that incorporates both audio and visual information\n".
               "2. 5-10 relevant tags (comma-separated) based on both transcript and visual content\n\n".
               "Transcript:\n{$transcript}{$visualContext}";
    }

    private function parseAIResponse(string $text): array
    {
        $lines = explode("\n", $text);
        $summary = '';
        $tags = [];

        foreach ($lines as $line) {
            if (stripos($line, 'summary') !== false || stripos($line, 'tags') === false) {
                $summary .= $line."\n";
            } elseif (stripos($line, 'tags') !== false) {
                $tagLine = str_replace(['Tags:', 'tags:', '-'], '', $line);
                $tags = array_map('trim', explode(',', $tagLine));
            }
        }

        return [
            'status' => 'success',
            'summary' => trim($summary),
            'tags' => array_filter($tags),
        ];
    }
}
