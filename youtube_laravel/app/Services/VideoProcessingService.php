<?php

namespace App\Services;

use App\Models\VideoDownload;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Storage;

class VideoProcessingService
{
    /**
     * Process final video by combining original video with synthesized audio
     * Optionally adds watermark and other effects
     */
    public function processFinalVideo(VideoDownload $video, ?string $watermarkPath = null): ?string
    {
        if (! $video->local_file || ! Storage::disk('public')->exists($video->local_file)) {
            Log::error('Original video file not found for video ID: '.$video->id);

            return null;
        }

        if (! $video->synthesized_audio_path || ! Storage::disk('public')->exists($video->synthesized_audio_path)) {
            Log::error('Synthesized audio file not found for video ID: '.$video->id);

            return null;
        }

        try {
            $videoPath = Storage::disk('public')->path($video->local_file);
            $audioPath = Storage::disk('public')->path($video->synthesized_audio_path);
            $outputFilename = 'processed_videos/final_'.($video->video_id ?? $video->id).'_'.time().'.mp4';
            $outputPath = Storage::disk('public')->path($outputFilename);

            // Ensure output directory exists
            $outputDir = dirname($outputPath);
            if (! is_dir($outputDir)) {
                mkdir($outputDir, 0755, true);
            }

            // Build ffmpeg command to replace audio
            $command = $this->buildFFmpegCommand($videoPath, $audioPath, $outputPath, $watermarkPath);

            exec($command, $output, $returnCode);

            if ($returnCode === 0 && file_exists($outputPath)) {
                // Update video model with processed video path
                $video->update([
                    'step_final_video_status' => 'completed',
                ]);

                return $outputFilename;
            } else {
                Log::error('FFmpeg processing failed for video ID: '.$video->id.' Return code: '.$returnCode);
                Log::error('FFmpeg output: '.implode("\n", $output));

                return null;
            }
        } catch (\Exception $e) {
            Log::error('Video processing error: '.$e->getMessage());

            return null;
        }
    }

    /**
     * Build FFmpeg command for video processing
     */
    private function buildFFmpegCommand(
        string $videoPath,
        string $audioPath,
        string $outputPath,
        ?string $watermarkPath = null
    ): string {
        $filters = [];

        // Add watermark if provided
        if ($watermarkPath && file_exists($watermarkPath)) {
            $filters[] = 'overlay=W-w-10:10'; // Position watermark at top-right
            $watermarkFilter = "movie={$watermarkPath}[watermark];[in][watermark]".implode('', $filters).'[out]';
        }

        // Build base command to replace audio
        $command = sprintf(
            'ffmpeg -i "%s" -i "%s" -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 -shortest -y "%s"',
            $videoPath,
            $audioPath,
            $outputPath
        );

        // Add watermark if provided
        if ($watermarkPath && file_exists($watermarkPath)) {
            $command = sprintf(
                'ffmpeg -i "%s" -i "%s" -i "%s" -filter_complex "[0:v][2:v]overlay=W-w-10:10[v]" -map "[v]" -map 1:a -c:a aac -shortest -y "%s"',
                $videoPath,
                $audioPath,
                $watermarkPath,
                $outputPath
            );
        }

        return $command;
    }

    /**
     * Get video duration in seconds
     */
    public function getVideoDuration(string $videoPath): ?float
    {
        try {
            $command = sprintf(
                'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "%s"',
                $videoPath
            );

            $duration = exec($command);

            return $duration ? (float) $duration : null;
        } catch (\Exception $e) {
            return null;
        }
    }

    /**
     * Extract thumbnail from video
     */
    public function extractThumbnail(VideoDownload $video, int $timestamp = 1): ?string
    {
        if (! $video->local_file || ! Storage::disk('public')->exists($video->local_file)) {
            return null;
        }

        try {
            $videoPath = Storage::disk('public')->path($video->local_file);
            $thumbnailFilename = 'thumbnails/thumb_'.($video->video_id ?? $video->id).'_'.time().'.jpg';
            $thumbnailPath = Storage::disk('public')->path($thumbnailFilename);

            // Ensure output directory exists
            $outputDir = dirname($thumbnailPath);
            if (! is_dir($outputDir)) {
                mkdir($outputDir, 0755, true);
            }

            $command = sprintf(
                'ffmpeg -i "%s" -ss %d -vframes 1 -q:v 2 -y "%s"',
                $videoPath,
                $timestamp,
                $thumbnailPath
            );

            exec($command, $output, $returnCode);

            if ($returnCode === 0 && file_exists($thumbnailPath)) {
                return $thumbnailFilename;
            }

            return null;
        } catch (\Exception $e) {
            Log::error('Thumbnail extraction error: '.$e->getMessage());

            return null;
        }
    }
}
