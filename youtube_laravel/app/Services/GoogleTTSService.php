<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Storage;

class GoogleTTSService
{
    private ?string $apiKey;

    public function __construct()
    {
        $this->apiKey = config('services.google_tts.api_key');
    }

    /**
     * Synthesize speech from text using Google TTS API
     *
     * @param  string  $text  Text to synthesize
     * @param  string  $languageCode  Language code (e.g., 'hi-IN', 'en-US')
     * @param  string  $voiceName  Voice name (e.g., 'hi-IN-Standard-A', 'en-US-Standard-B')
     * @param  string|null  $outputPath  Path to save audio file
     * @param  int|null  $targetDuration  Target duration in seconds (for speed adjustment)
     * @return bool Success status
     */
    public function synthesize(
        string $text,
        string $languageCode = 'hi-IN',
        string $voiceName = 'hi-IN-Standard-A',
        ?string $outputPath = null,
        ?int $targetDuration = null
    ): bool {
        if (! $this->apiKey) {
            Log::error('Google TTS API key not configured');

            return false;
        }

        try {
            // Split text into chunks if too long (Google TTS has limits)
            $chunks = $this->splitTextIntoChunks($text, 5000); // 5000 characters per chunk

            $audioData = '';

            foreach ($chunks as $chunk) {
                $response = Http::timeout(60)
                    ->post("https://texttospeech.googleapis.com/v1/text:synthesize?key={$this->apiKey}", [
                        'input' => [
                            'text' => $chunk,
                        ],
                        'voice' => [
                            'languageCode' => $languageCode,
                            'name' => $voiceName,
                        ],
                        'audioConfig' => [
                            'audioEncoding' => 'MP3',
                            'speakingRate' => 1.0, // Normal speed
                            'pitch' => 0.0, // Normal pitch
                        ],
                    ]);

                if ($response->successful()) {
                    $data = $response->json();
                    $audioContent = base64_decode($data['audioContent'] ?? '');
                    $audioData .= $audioContent;
                } else {
                    Log::error('Google TTS API error: '.$response->body());

                    return false;
                }
            }

            // Save audio file
            if ($outputPath && $audioData) {
                Storage::disk('public')->put($outputPath, $audioData);

                // Adjust duration if needed
                if ($targetDuration) {
                    $this->adjustAudioDuration($outputPath, $targetDuration);
                }

                return true;
            }

            return false;
        } catch (\Exception $e) {
            Log::error('Google TTS error: '.$e->getMessage());

            return false;
        }
    }

    /**
     * Split long text into chunks for TTS
     */
    private function splitTextIntoChunks(string $text, int $maxLength): array
    {
        $chunks = [];
        $sentences = preg_split('/([.!?]+)/', $text, -1, PREG_SPLIT_DELIM_CAPTURE);

        $currentChunk = '';
        foreach ($sentences as $sentence) {
            if (strlen($currentChunk.$sentence) > $maxLength) {
                if ($currentChunk) {
                    $chunks[] = trim($currentChunk);
                }
                $currentChunk = $sentence;
            } else {
                $currentChunk .= $sentence;
            }
        }

        if ($currentChunk) {
            $chunks[] = trim($currentChunk);
        }

        return $chunks;
    }

    /**
     * Adjust audio duration to match video duration
     */
    private function adjustAudioDuration(string $audioPath, int $targetDuration): void
    {
        try {
            $fullPath = Storage::disk('public')->path($audioPath);
            $tempPath = storage_path('app/temp/'.basename($audioPath));

            // Get current audio duration
            $currentDuration = $this->getAudioDuration($fullPath);

            if ($currentDuration && abs($currentDuration - $targetDuration) > 1) {
                // Calculate speed adjustment
                $speed = $currentDuration / $targetDuration;

                // Use ffmpeg to adjust speed
                $command = sprintf(
                    'ffmpeg -i "%s" -filter:a "atempo=%.2f" "%s" -y',
                    $fullPath,
                    $speed,
                    $tempPath
                );

                exec($command, $output, $returnCode);

                if ($returnCode === 0 && file_exists($tempPath)) {
                    // Replace original with adjusted audio
                    copy($tempPath, $fullPath);
                    unlink($tempPath);
                }
            }
        } catch (\Exception $e) {
            Log::error('Audio duration adjustment error: '.$e->getMessage());
        }
    }

    /**
     * Get audio file duration in seconds
     */
    private function getAudioDuration(string $audioPath): ?float
    {
        try {
            $command = sprintf(
                'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "%s"',
                $audioPath
            );

            $duration = exec($command);

            return $duration ? (float) $duration : null;
        } catch (\Exception $e) {
            return null;
        }
    }
}
