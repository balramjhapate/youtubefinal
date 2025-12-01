<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Storage;

class VideoDownloadService
{
    public function download(string $videoUrl, string $filename): ?string
    {
        try {
            $response = Http::timeout(300)->get($videoUrl);

            if ($response->successful()) {
                $path = 'videos/'.$filename;
                Storage::disk('public')->put($path, $response->body());

                return $path;
            }
        } catch (\Exception $e) {
            Log::error('Video download error: '.$e->getMessage());
        }

        return null;
    }
}
