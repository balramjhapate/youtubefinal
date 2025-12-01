<?php

namespace App\Http\Controllers;

use App\Models\VideoDownload;
use Inertia\Inertia;
use Inertia\Response;

class DashboardController extends Controller
{
    public function index(): Response
    {
        $stats = [
            'total_videos' => VideoDownload::count(),
            'successful_videos' => VideoDownload::where('status', 'success')->count(),
            'failed_videos' => VideoDownload::where('status', 'failed')->count(),
            'pending_videos' => VideoDownload::where('status', 'pending')->count(),
            'downloaded_videos' => VideoDownload::where('is_downloaded', true)->count(),
            'transcribed_videos' => VideoDownload::where('transcription_status', 'transcribed')->count(),
            'transcribing_videos' => VideoDownload::where('transcription_status', 'transcribing')->count(),
            'ai_processed_videos' => VideoDownload::where('ai_processing_status', 'processed')->count(),
            'ai_processing_videos' => VideoDownload::where('ai_processing_status', 'processing')->count(),
            'prompts_generated' => VideoDownload::where('audio_prompt_status', 'generated')->count(),
            'tts_completed_videos' => VideoDownload::where('step_tts_synthesis_status', 'completed')->count(),
            'final_processed_videos' => VideoDownload::where('step_final_video_status', 'completed')->count(),
            'recent_videos' => VideoDownload::latest()->take(10)->get()->map(function ($video) {
                return [
                    'id' => $video->id,
                    'title' => $video->title,
                    'cover_url' => $video->cover_url,
                    'status' => $video->status,
                    'transcription_status' => $video->transcription_status,
                    'ai_processing_status' => $video->ai_processing_status,
                    'is_downloaded' => $video->is_downloaded,
                    'audio_prompt_status' => $video->audio_prompt_status,
                    'step_tts_synthesis_status' => $video->step_tts_synthesis_status,
                    'step_script_generation_status' => $video->step_script_generation_status,
                    'created_at' => $video->created_at->diffForHumans(),
                ];
            }),
        ];

        return Inertia::render('Dashboard', [
            'stats' => $stats,
        ]);
    }
}
