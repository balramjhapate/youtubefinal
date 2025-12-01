<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class AIOptimizationService
{
    /**
     * Compare and optimize transcript based on visual analysis
     * This creates a more accurate and context-aware transcript
     */
    public function optimizeTranscript(string $transcript, array $visualAnalysis): array
    {
        $apiKey = config('services.gemini.api_key');
        if (! $apiKey) {
            return [
                'status' => 'error',
                'optimized_transcript' => $transcript, // Fallback to original
            ];
        }

        // Build prompt with transcript and visual context
        $visualContext = $this->buildVisualContext($visualAnalysis);

        $prompt = "You are analyzing a video transcript along with visual frame descriptions.\n\n".
                  "Transcript:\n{$transcript}\n\n".
                  "Visual Context (from video frames):\n{$visualContext}\n\n".
                  "Please:\n".
                  "1. Compare the transcript with visual context\n".
                  "2. Identify any discrepancies or missing information\n".
                  "3. Optimize the transcript to include visual context where relevant\n".
                  "4. Generate a clean, accurate, and contextually rich transcript\n".
                  "5. Remove filler words, repetitions, and improve clarity\n\n".
                  'Return only the optimized transcript text.';

        try {
            $response = Http::timeout(60)
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
                $optimizedText = $data['candidates'][0]['content']['parts'][0]['text'] ?? '';

                return [
                    'status' => 'success',
                    'optimized_transcript' => trim($optimizedText),
                    'original_transcript' => $transcript,
                ];
            }
        } catch (\Exception $e) {
            Log::error('AI optimization error: '.$e->getMessage());
        }

        return [
            'status' => 'error',
            'optimized_transcript' => $transcript, // Fallback to original
        ];
    }

    private function buildVisualContext(array $visualAnalysis): string
    {
        $context = [];
        foreach ($visualAnalysis as $analysis) {
            $context[] = sprintf(
                '[%ds] %s - Objects: %s',
                $analysis['timestamp'] ?? 0,
                $analysis['description'] ?? '',
                implode(', ', $analysis['objects'] ?? [])
            );
        }

        return implode("\n", $context);
    }
}
