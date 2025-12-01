<?php

namespace App\Http\Controllers;

use App\Http\Requests\ExtractVideoRequest;
use App\Jobs\ProcessAIJob;
use App\Jobs\ProcessFinalVideoJob;
use App\Jobs\ProcessVideoPipeline;
use App\Jobs\SynthesizeAudioJob;
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
        $source = $request->input('source', 'xiaohongshu');
        
        // For local upload, handle file upload differently
        if ($source === 'local') {
            // TODO: Implement local file upload handling
            return back()->withErrors(['url' => 'Local upload is not yet implemented']);
        }
        
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

        // Start background processing pipeline
        ProcessVideoPipeline::dispatch($video->id);

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

    public function synthesize(VideoDownload $video, Request $request): RedirectResponse
    {
        if ($video->step_tts_synthesis_status === 'processing') {
            return back()->withErrors(['error' => 'TTS synthesis already in progress']);
        }

        if (! $video->transcript_clean_script) {
            return back()->withErrors(['error' => 'Clean script not found. Please complete transcription first.']);
        }

        $languageCode = $request->input('language_code', 'hi-IN');
        $voiceName = $request->input('voice_name', 'hi-IN-Standard-A');

        SynthesizeAudioJob::dispatch($video->id, $languageCode, $voiceName);

        return back()->with('message', 'TTS synthesis started');
    }

    public function processFinalVideo(VideoDownload $video): RedirectResponse
    {
        if ($video->step_final_video_status === 'processing') {
            return back()->withErrors(['error' => 'Video processing already in progress']);
        }

        if (! $video->local_file) {
            return back()->withErrors(['error' => 'Original video not found. Please download video first.']);
        }

        if (! $video->synthesized_audio_path) {
            return back()->withErrors(['error' => 'Synthesized audio not found. Please synthesize audio first.']);
        }

        ProcessFinalVideoJob::dispatch($video->id);

        return back()->with('message', 'Final video processing started');
    }

    public function bulkDelete(Request $request): RedirectResponse
    {
        $validated = $request->validate([
            'video_ids' => 'required|array',
            'video_ids.*' => 'required|integer|exists:video_downloads,id',
        ]);

        $count = VideoDownload::whereIn('id', $validated['video_ids'])->delete();

        return back()->with('message', "{$count} video(s) deleted successfully");
    }

    public function bulkProcess(Request $request): RedirectResponse
    {
        $validated = $request->validate([
            'video_ids' => 'required|array',
            'video_ids.*' => 'required|integer|exists:video_downloads,id',
            'action' => 'required|string|in:transcribe,process_ai,synthesize,process_final',
        ]);

        $videos = VideoDownload::whereIn('id', $validated['video_ids'])->get();
        $count = 0;

        foreach ($videos as $video) {
            switch ($validated['action']) {
                case 'transcribe':
                    if ($video->is_downloaded && $video->transcription_status !== 'transcribing') {
                        TranscribeVideoJob::dispatch($video->id);
                        $count++;
                    }
                    break;
                case 'process_ai':
                    if ($video->transcription_status === 'transcribed' && $video->ai_processing_status !== 'processing') {
                        ProcessAIJob::dispatch($video->id);
                        $count++;
                    }
                    break;
                case 'synthesize':
                    if ($video->transcript_clean_script && $video->step_tts_synthesis_status !== 'processing') {
                        SynthesizeAudioJob::dispatch($video->id);
                        $count++;
                    }
                    break;
                case 'process_final':
                    if ($video->synthesized_audio_path && $video->step_final_video_status !== 'processing') {
                        ProcessFinalVideoJob::dispatch($video->id);
                        $count++;
                    }
                    break;
            }
        }

        return back()->with('message', "Bulk {$validated['action']} started for {$count} video(s)");
    }

    public function retryTranscription(VideoDownload $video): RedirectResponse
    {
        if ($video->transcription_status === 'failed' || $video->transcription_status === 'not_transcribed') {
            TranscribeVideoJob::dispatch($video->id);

            return back()->with('message', 'Transcription retry started');
        }

        return back()->withErrors(['error' => 'Video is not in a failed state']);
    }

    public function retryAIProcessing(VideoDownload $video): RedirectResponse
    {
        if ($video->ai_processing_status === 'failed' || $video->ai_processing_status === 'not_processed') {
            ProcessAIJob::dispatch($video->id);

            return back()->with('message', 'AI processing retry started');
        }

        return back()->withErrors(['error' => 'AI processing is not in a failed state']);
    }

    public function retryTTS(VideoDownload $video): RedirectResponse
    {
        if ($video->step_tts_synthesis_status === 'failed') {
            SynthesizeAudioJob::dispatch($video->id);

            return back()->with('message', 'TTS synthesis retry started');
        }

        return back()->withErrors(['error' => 'TTS synthesis is not in a failed state']);
    }

    public function retryFinalVideo(VideoDownload $video): RedirectResponse
    {
        if ($video->step_final_video_status === 'failed') {
            ProcessFinalVideoJob::dispatch($video->id);

            return back()->with('message', 'Final video processing retry started');
        }

        return back()->withErrors(['error' => 'Final video processing is not in a failed state']);
    }

    public function reprocess(VideoDownload $video): RedirectResponse
    {
        ProcessVideoPipeline::dispatch($video->id);

        return back()->with('message', 'Video reprocessing started');
    }

    public function destroy(VideoDownload $video): RedirectResponse
    {
        $video->delete();

        return back()->with('message', 'Video deleted successfully');
    }
}
