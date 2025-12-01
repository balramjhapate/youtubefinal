<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class ScriptGenerationService
{
    /**
     * Generate clean script optimized for TTS
     * Removes timestamps, filler words, and formats for natural speech
     */
    public function generateCleanScript(string $optimizedTranscript, string $targetLanguage = 'hi'): array
    {
        $apiKey = config('services.gemini.api_key');
        if (! $apiKey) {
            return [
                'status' => 'error',
                'clean_script' => $optimizedTranscript, // Fallback
            ];
        }

        $prompt = "Convert this transcript into a clean script optimized for Text-to-Speech synthesis.\n\n".
                  "Requirements:\n".
                  "1. Remove all timestamps and timestamps markers\n".
                  "2. Remove filler words (um, uh, like, etc.)\n".
                  "3. Fix grammar and sentence structure\n".
                  "4. Break into natural speech segments\n".
                  "5. Ensure smooth flow for TTS reading\n".
                  "6. Translate to {$targetLanguage} if needed\n\n".
                  "Transcript:\n{$optimizedTranscript}\n\n".
                  'Return only the clean script text, ready for TTS.';

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
                $cleanScript = $data['candidates'][0]['content']['parts'][0]['text'] ?? '';

                return [
                    'status' => 'success',
                    'clean_script' => trim($cleanScript),
                ];
            }
        } catch (\Exception $e) {
            Log::error('Script generation error: '.$e->getMessage());
        }

        return [
            'status' => 'error',
            'clean_script' => $optimizedTranscript, // Fallback
        ];
    }
}
