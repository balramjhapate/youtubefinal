<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class VisualAnalysisService
{
    /**
     * Analyze video frames using AI vision model
     * This helps optimize the transcript by understanding visual context
     */
    public function analyzeFrames(array $frames, string $transcript): array
    {
        $analysis = [];

        foreach ($frames as $frame) {
            try {
                // Option 1: Use Gemini Vision API
                $frameAnalysis = $this->analyzeFrameWithGemini($frame['path']);

                // Option 2: Use OpenAI Vision API
                // $frameAnalysis = $this->analyzeFrameWithOpenAI($frame['path']);

                $analysis[] = [
                    'timestamp' => $frame['timestamp'],
                    'description' => $frameAnalysis['description'] ?? '',
                    'objects' => $frameAnalysis['objects'] ?? [],
                ];
            } catch (\Exception $e) {
                Log::error('Frame analysis error: '.$e->getMessage());
            }
        }

        return $analysis;
    }

    private function analyzeFrameWithGemini(string $framePath): array
    {
        $apiKey = config('services.gemini.api_key');
        if (! $apiKey) {
            return ['description' => '', 'objects' => []];
        }

        $imageData = base64_encode(file_get_contents($framePath));

        try {
            $response = Http::timeout(30)
                ->post("https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent?key={$apiKey}", [
                    'contents' => [
                        [
                            'parts' => [
                                ['text' => 'Describe what you see in this video frame. List any objects, actions, or important visual elements.'],
                                [
                                    'inline_data' => [
                                        'mime_type' => 'image/jpeg',
                                        'data' => $imageData,
                                    ],
                                ],
                            ],
                        ],
                    ],
                ]);

            if ($response->successful()) {
                $data = $response->json();
                $description = $data['candidates'][0]['content']['parts'][0]['text'] ?? '';

                return [
                    'description' => $description,
                    'objects' => $this->extractObjects($description),
                ];
            }
        } catch (\Exception $e) {
            Log::error('Gemini vision API error: '.$e->getMessage());
        }

        return ['description' => '', 'objects' => []];
    }

    private function extractObjects(string $description): array
    {
        // Extract objects/entities from description
        // This is a simple implementation - can be enhanced with NLP
        $objects = [];
        $commonObjects = ['person', 'car', 'building', 'food', 'text', 'logo', 'product'];

        foreach ($commonObjects as $obj) {
            if (stripos($description, $obj) !== false) {
                $objects[] = $obj;
            }
        }

        return $objects;
    }
}
