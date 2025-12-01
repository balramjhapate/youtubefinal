<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class VideoExtractionService
{
    public function extract(string $url): ?array
    {
        // Try Seekin API first
        $result = $this->extractViaSeekin($url);
        if ($result) {
            return array_merge($result, ['method' => 'seekin']);
        }

        // Try yt-dlp (if available)
        $result = $this->extractViaYtDlp($url);
        if ($result) {
            return array_merge($result, ['method' => 'yt-dlp']);
        }

        // Try direct requests
        $result = $this->extractViaRequests($url);
        if ($result) {
            return array_merge($result, ['method' => 'requests']);
        }

        return null;
    }

    private function extractViaSeekin(string $url): ?array
    {
        try {
            $response = Http::timeout(15)->post('https://api.seekin.ai/ikool/media/download', [
                'url' => $url,
            ], [
                'Content-Type' => 'application/json',
                'User-Agent' => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            ]);

            $data = $response->json();

            if (isset($data['code']) && $data['code'] === '0000' && isset($data['data'])) {
                $videoData = $data['data'];
                $medias = $videoData['medias'] ?? [];
                
                if (!empty($medias)) {
                    $bestMedia = collect($medias)->sortByDesc('fileSize')->first();
                    
                    return [
                        'video_url' => $bestMedia['url'] ?? null,
                        'title' => $videoData['title'] ?? 'Xiaohongshu Video',
                        'cover_url' => $videoData['imageUrl'] ?? null,
                        'original_title' => $videoData['title'] ?? '',
                        'original_description' => $videoData['title'] ?? '',
                        'duration' => $videoData['duration'] ?? 0,
                    ];
                }
            }
        } catch (\Exception $e) {
            Log::error('Seekin API error: ' . $e->getMessage());
        }

        return null;
    }

    private function extractViaYtDlp(string $url): ?array
    {
        // Implement yt-dlp extraction if needed
        // This would require installing yt-dlp or using a PHP wrapper
        return null;
    }

    private function extractViaRequests(string $url): ?array
    {
        // Implement direct HTTP requests extraction if needed
        return null;
    }

    public function extractVideoId(string $url): ?string
    {
        if (preg_match('/\/item\/([a-zA-Z0-9]+)/', parse_url($url, PHP_URL_PATH), $matches)) {
            return $matches[1];
        }
        return null;
    }
}

