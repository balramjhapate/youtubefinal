<?php

namespace App\Http\Controllers;

use App\Http\Requests\ExtractVideoRequest;
use App\Jobs\ProcessAIJob;
use App\Jobs\TranscribeVideoJob;
use App\Models\VideoDownload;
use App\Services\TranslationService;
use App\Services\VideoDownloadService;
use App\Services\VideoExtractionService;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;

class VideoController extends Controller
{
    public function __construct(
        private VideoExtractionService $extractionService,
        private TranslationService $translationService
    ) {}

    public function extract(ExtractVideoRequest $request): RedirectResponse
    {
        $url = $request->url;
        $videoId = $this->extractionService->extractVideoId($url);

        // Check if video already exists
        if ($videoId) {
            $existing = VideoDownload::where('video_id', $videoId)->first();
            if ($existing && $existing->status === 'success') {
                return redirect()->route('videos.show', $existing->id)
                    ->with('message', 'Video already exists');
            }
        }

        // Extract video
        $videoData = $this->extractionService->extract($url);

        if (! $videoData) {
            return back()->withErrors(['url' => 'Could not extract video']);
        }

        // Create video record
        $video = VideoDownload::create([
            'url' => $url,
            'video_id' => $videoId,
            'video_url' => $videoData['video_url'],
            'cover_url' => $videoData['cover_url'],
            'original_title' => $videoData['original_title'],
            'original_description' => $videoData['original_description'],
            'title' => $this->translationService->translate($videoData['original_title'], 'en'),
            'description' => $this->translationService->translate($videoData['original_description'], 'en'),
            'duration' => $videoData['duration'] ?? 0,
            'extraction_method' => $videoData['method'],
            'status' => 'success',
        ]);

        // TODO: Start background processing when ProcessVideoPipeline job is created
        // ProcessVideoPipeline::dispatch($video->id);

        return redirect()->route('videos.show', $video->id)
            ->with('message', 'Video extracted successfully. Processing started.');
    }

    public function index(Request $request)
    {
        $query = VideoDownload::query();

        // Apply filters
        if ($request->has('status')) {
            $query->where('status', $request->status);
        }

        if ($request->has('transcription_status')) {
            $query->where('transcription_status', $request->transcription_status);
        }

        if ($request->has('search')) {
            $query->where('title', 'like', '%'.$request->search.'%');
        }

        $videos = $query->latest()->paginate(20);

        return \Inertia\Inertia::render('Videos/Index', [
            'videos' => $videos,
            'filters' => $request->only(['status', 'transcription_status', 'search']),
        ]);
    }

    public function show(VideoDownload $video)
    {
        return \Inertia\Inertia::render('Videos/Show', [
            'video' => $video,
        ]);
    }

    public function download(VideoDownload $video): RedirectResponse
    {
        if (! $video->video_url) {
            return back()->withErrors(['error' => 'No video URL found']);
        }

        $service = app(VideoDownloadService::class);
        $filename = ($video->video_id ?? 'video').'_'.$video->id.'.mp4';
        $path = $service->download($video->video_url, $filename);

        if ($path) {
            $video->update([
                'local_file' => $path,
                'is_downloaded' => true,
            ]);

            return back()->with('message', 'Video downloaded successfully');
        }

        return back()->withErrors(['error' => 'Failed to download video']);
    }

    public function transcribe(VideoDownload $video): RedirectResponse
    {
        if ($video->transcription_status === 'transcribing') {
            return back()->withErrors(['error' => 'Transcription already in progress']);
        }

        TranscribeVideoJob::dispatch($video->id);

        return back()->with('message', 'Transcription started');
    }

    public function processAI(VideoDownload $video): RedirectResponse
    {
        if ($video->ai_processing_status === 'processing') {
            return back()->withErrors(['error' => 'AI processing already in progress']);
        }

        ProcessAIJob::dispatch($video->id);

        return back()->with('message', 'AI processing started');
    }
}
