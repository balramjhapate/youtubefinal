# Module-Wise Migration Guide: Django → Laravel

## 📋 Migration Strategy

This guide breaks down the migration into **12 modules**. Complete them **one by one** in order. Each module includes:
- ✅ Old Django code reference
- ✅ New Laravel implementation
- ✅ Step-by-step instructions
- ✅ Example requests/responses
- ✅ Testing checklist
- ✅ Completion status

---

## 🎯 Module Completion Order

1. [Module 1: Project Setup & Database](#module-1-project-setup--database) ⬜
2. [Module 2: Video Extraction](#module-2-video-extraction) ⬜
3. [Module 3: Video Listing & Detail](#module-3-video-listing--detail) ⬜
4. [Module 4: Video Download](#module-4-video-download) ⬜
5. [Module 5: Transcription](#module-5-transcription) ⬜
6. [Module 6: AI Processing](#module-6-ai-processing) ⬜
7. [Module 7: TTS Synthesis](#module-7-tts-synthesis) ⬜
8. [Module 8: Video Processing](#module-8-video-processing) ⬜
9. [Module 9: Settings Management](#module-9-settings-management) ⬜
10. [Module 10: Bulk Operations](#module-10-bulk-operations) ⬜
11. [Module 11: Retry Operations](#module-11-retry-operations) ⬜
12. [Module 12: Dashboard & Statistics](#module-12-dashboard--statistics) ⬜

---

## 📦 Module 1: Project Setup & Database

### Status: ⬜ Not Started | 🟡 In Progress | ✅ Completed

### Old Django Reference

**File**: `backend/downloader/models.py`

```python
class VideoDownload(models.Model):
    url = models.URLField(max_length=500)
    video_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    title = models.CharField(max_length=500, blank=True)
    # ... many more fields
```

### New Laravel Implementation

#### Step 1: Create Migration

```bash
php artisan make:migration create_video_downloads_table
```

**File**: `database/migrations/YYYY_MM_DD_HHMMSS_create_video_downloads_table.php`

```php
<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('video_downloads', function (Blueprint $table) {
            $table->id();
            $table->string('url', 500);
            $table->string('video_id', 100)->nullable()->unique();
            
            // Content
            $table->string('title', 500)->nullable();
            $table->string('original_title', 500)->nullable();
            $table->text('description')->nullable();
            $table->text('original_description')->nullable();
            
            // Media
            $table->string('video_url', 1000)->nullable();
            $table->string('cover_url', 1000)->nullable();
            $table->string('local_file')->nullable();
            $table->boolean('is_downloaded')->default(false);
            $table->integer('duration')->default(0);
            
            // Metadata
            $table->string('extraction_method', 20)->nullable();
            $table->enum('status', ['success', 'failed', 'pending'])->default('pending');
            $table->text('error_message')->nullable();
            
            // AI Processing
            $table->enum('ai_processing_status', [
                'not_processed', 'processing', 'processed', 'failed'
            ])->default('not_processed');
            $table->timestamp('ai_processed_at')->nullable();
            $table->text('ai_summary')->nullable();
            $table->string('ai_tags', 500)->nullable();
            $table->text('ai_error_message')->nullable();
            
            // Transcription
            $table->enum('transcription_status', [
                'not_transcribed', 'transcribing', 'transcribed', 'failed'
            ])->default('not_transcribed');
            $table->text('transcript')->nullable();
            $table->text('transcript_hindi')->nullable();
            $table->string('transcript_language', 10)->nullable();
            $table->timestamp('transcript_started_at')->nullable();
            $table->timestamp('transcript_processed_at')->nullable();
            $table->text('transcript_error_message')->nullable();
            
            // Audio Prompt
            $table->enum('audio_prompt_status', [
                'not_generated', 'generating', 'generated', 'failed'
            ])->default('not_generated');
            $table->text('audio_generation_prompt')->nullable();
            $table->timestamp('audio_prompt_generated_at')->nullable();
            $table->text('audio_prompt_error')->nullable();
            
            // Processing V2
            $table->string('processing_v2_status', 50)->default('not_started');
            $table->string('processing_v2_current_step', 100)->nullable();
            $table->text('processing_v2_log')->nullable();
            $table->timestamp('processing_v2_started_at')->nullable();
            $table->timestamp('processing_v2_completed_at')->nullable();
            
            // Step-specific statuses
            $table->string('step_download_status', 20)->default('pending');
            $table->string('step_transcription_status', 20)->default('pending');
            $table->string('step_ai_enhancement_status', 20)->default('pending');
            $table->string('step_script_generation_status', 20)->default('pending');
            $table->string('step_tts_synthesis_status', 20)->default('pending');
            $table->string('step_final_video_status', 20)->default('pending');
            $table->string('step_upload_sync_status', 20)->default('pending');
            
            // Additional fields for enhanced workflow
            $table->text('transcript_optimized')->nullable(); // AI-optimized transcript
            $table->text('transcript_clean_script')->nullable(); // Clean script for TTS
            $table->text('visual_analysis')->nullable(); // JSON: Visual frame analysis
            $table->string('synthesized_audio_path')->nullable(); // Google TTS audio file path
            $table->timestamp('synthesized_at')->nullable();
            $table->text('synthesis_error')->nullable();
            
            $table->timestamps();
            
            $table->index('status');
            $table->index('transcription_status');
            $table->index('ai_processing_status');
            $table->index('created_at');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('video_downloads');
    }
};
```

#### Step 2: Create Model

```bash
php artisan make:model VideoDownload
```

**File**: `app/Models/VideoDownload.php`

```php
<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Casts\Attribute;

class VideoDownload extends Model
{
    protected $fillable = [
        'url', 'video_id', 'title', 'original_title', 'description',
        'original_description', 'video_url', 'cover_url', 'local_file',
        'is_downloaded', 'duration', 'extraction_method', 'status',
        'error_message', 'ai_processing_status', 'ai_processed_at',
        'ai_summary', 'ai_tags', 'ai_error_message', 'transcription_status',
        'transcript', 'transcript_hindi', 'transcript_language',
        'transcript_started_at', 'transcript_processed_at',
        'transcript_error_message', 'audio_prompt_status',
        'audio_generation_prompt', 'audio_prompt_generated_at',
        'audio_prompt_error', 'processing_v2_status',
        'processing_v2_current_step', 'processing_v2_log',
        'processing_v2_started_at', 'processing_v2_completed_at',
        'step_download_status', 'step_transcription_status',
        'step_ai_enhancement_status', 'step_script_generation_status',
        'step_tts_synthesis_status', 'step_final_video_status',
        'step_upload_sync_status',
    ];

    protected $casts = [
        'is_downloaded' => 'boolean',
        'duration' => 'integer',
        'ai_processed_at' => 'datetime',
        'transcript_started_at' => 'datetime',
        'transcript_processed_at' => 'datetime',
        'audio_prompt_generated_at' => 'datetime',
        'processing_v2_started_at' => 'datetime',
        'processing_v2_completed_at' => 'datetime',
        'processing_v2_log' => 'array',
    ];

    public function isSuccessful(): bool
    {
        return $this->status === 'success';
    }

    public function isAIProcessed(): bool
    {
        return $this->ai_processing_status === 'processed';
    }

    public function getProcessingLogAttribute($value)
    {
        if (empty($value)) {
            return [];
        }
        return json_decode($value, true) ?? [];
    }

    public function setProcessingLogAttribute($value)
    {
        $this->attributes['processing_v2_log'] = json_encode($value ?? []);
    }
}
```

#### Step 3: Run Migration

```bash
php artisan migrate
```

### Testing Checklist

- [ ] Migration runs without errors
- [ ] Model can be created: `VideoDownload::create(['url' => 'test'])`
- [ ] Model can be retrieved: `VideoDownload::find(1)`
- [ ] All fields are accessible
- [ ] Enums work correctly
- [ ] Timestamps are set automatically

### Completion Notes

**Date Completed**: _______________
**Issues Encountered**: _______________
**Additional Notes**: _______________

---

## 📦 Module 2: Video Extraction

### Status: ⬜ Not Started | 🟡 In Progress | ✅ Completed

### Old Django Reference

**File**: `backend/downloader/views.py` - `extract_video()` function
**File**: `backend/downloader/utils.py` - `perform_extraction()`, `extract_video_seekin()`

**Django Endpoint**: `POST /api/videos/extract/`

**Django Request**:
```json
{
  "url": "https://www.xiaohongshu.com/explore/..."
}
```

**Django Response**:
```json
{
  "video_url": "https://...",
  "title": "Video Title",
  "cover_url": "https://...",
  "method": "seekin",
  "id": 1,
  "auto_processing": true,
  "message": "Video extracted. Auto-processing started in background."
}
```

### New Laravel Implementation

#### Step 1: Create Service

```bash
php artisan make:service VideoExtractionService
```

**File**: `app/Services/VideoExtractionService.php`

```php
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
```

#### Step 2: Create Form Request (Validation)

```bash
php artisan make:request ExtractVideoRequest
```

**File**: `app/Http/Requests/ExtractVideoRequest.php`

```php
<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class ExtractVideoRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'url' => 'required|url|max:500',
        ];
    }
}
```

#### Step 3: Create Controller Method

**File**: `app/Http/Controllers/VideoController.php`

```php
<?php

namespace App\Http\Controllers;

use App\Http\Requests\ExtractVideoRequest;
use App\Models\VideoDownload;
use App\Services\VideoExtractionService;
use App\Services\TranslationService;
use App\Jobs\ProcessVideoPipeline;
use Illuminate\Http\Request;
use Inertia\Inertia;

class VideoController extends Controller
{
    public function __construct(
        private VideoExtractionService $extractionService,
        private TranslationService $translationService
    ) {}

    public function extract(ExtractVideoRequest $request)
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

        if (!$videoData) {
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

        // Start background processing
        ProcessVideoPipeline::dispatch($video->id);

        return redirect()->route('videos.show', $video->id)
            ->with('message', 'Video extracted successfully. Processing started.');
    }
}
```

#### Step 4: Add Route

**File**: `routes/web.php`

```php
Route::post('/videos/extract', [VideoController::class, 'extract'])->name('videos.extract');
```

#### Step 5: Create Frontend Form

**File**: `resources/js/Pages/Videos/Extract.jsx`

```jsx
import { Head, useForm } from '@inertiajs/react';
import { useState } from 'react';
import Layout from '@/Components/Layout';

export default function Extract() {
    const { data, setData, post, processing, errors } = useForm({
        url: '',
    });

    const handleSubmit = (e) => {
        e.preventDefault();
        post('/videos/extract', {
            preserveScroll: true,
        });
    };

    return (
        <Layout>
            <Head title="Extract Video" />
            
            <div className="container mx-auto px-4 py-8">
                <h1 className="text-3xl font-bold mb-6">Extract Video from URL</h1>
                
                <form onSubmit={handleSubmit} className="max-w-2xl">
                    <div className="mb-4">
                        <label htmlFor="url" className="block text-sm font-medium mb-2">
                            Xiaohongshu URL
                        </label>
                        <input
                            type="url"
                            id="url"
                            value={data.url}
                            onChange={(e) => setData('url', e.target.value)}
                            className="w-full border rounded px-4 py-2"
                            placeholder="https://www.xiaohongshu.com/explore/..."
                            required
                        />
                        {errors.url && (
                            <p className="text-red-500 text-sm mt-1">{errors.url}</p>
                        )}
                    </div>
                    
                    <button
                        type="submit"
                        disabled={processing}
                        className="bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600 disabled:opacity-50"
                    >
                        {processing ? 'Extracting...' : 'Extract Video'}
                    </button>
                </form>
            </div>
        </Layout>
    );
}
```

### Example Request/Response

**Request** (Inertia.js):
```javascript
router.post('/videos/extract', { url: 'https://www.xiaohongshu.com/explore/...' })
```

**Response** (Redirect to video detail page):
- Redirects to `/videos/{id}`
- Flash message: "Video extracted successfully. Processing started."

### Testing Checklist

- [ ] Service extracts video from Seekin API
- [ ] Service handles errors gracefully
- [ ] Controller validates URL
- [ ] Controller checks for duplicate videos
- [ ] Controller creates video record
- [ ] Controller dispatches background job
- [ ] Frontend form submits correctly
- [ ] Frontend shows validation errors
- [ ] Success redirects to video detail page

### Completion Notes

**Date Completed**: _______________
**Issues Encountered**: _______________
**Additional Notes**: _______________

---

## 📦 Module 3: Video Listing & Detail

### Status: ⬜ Not Started | 🟡 In Progress | ✅ Completed

### Old Django Reference

**File**: `backend/downloader/views.py`
- `list_videos()` - GET `/api/videos/`
- `get_video()` - GET `/api/videos/<id>/`

**Django Request** (List):
```
GET /api/videos/?status=success&transcription_status=transcribed&search=test
```

**Django Response** (List):
```json
[
  {
    "id": 1,
    "url": "https://...",
    "title": "Video Title",
    "status": "success",
    "transcription_status": "transcribed",
    "ai_processing_status": "processed",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

**Django Response** (Detail):
```json
{
  "id": 1,
  "url": "https://...",
  "title": "Video Title",
  "transcript": "Full transcript...",
  "ai_summary": "Summary...",
  "status": "success"
}
```

### New Laravel Implementation

#### Step 1: Create Controller Methods

**File**: `app/Http/Controllers/VideoController.php`

```php
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
        $query->where('title', 'like', '%' . $request->search . '%');
    }

    $videos = $query->latest()->paginate(20);

    return Inertia::render('Videos/Index', [
        'videos' => $videos,
        'filters' => $request->only(['status', 'transcription_status', 'search']),
    ]);
}

public function show(VideoDownload $video)
{
    return Inertia::render('Videos/Show', [
        'video' => $video,
    ]);
}
```

#### Step 2: Add Routes

**File**: `routes/web.php`

```php
Route::get('/videos', [VideoController::class, 'index'])->name('videos.index');
Route::get('/videos/{video}', [VideoController::class, 'show'])->name('videos.show');
```

#### Step 3: Create Frontend Pages

**File**: `resources/js/Pages/Videos/Index.jsx`

```jsx
import { Head, Link, router } from '@inertiajs/react';
import { useState } from 'react';
import Layout from '@/Components/Layout';

export default function Index({ videos, filters }) {
    const [search, setSearch] = useState(filters.search || '');

    const handleSearch = (e) => {
        e.preventDefault();
        router.get('/videos', { search }, {
            preserveState: true,
            preserveScroll: true,
        });
    };

    return (
        <Layout>
            <Head title="Videos" />
            
            <div className="container mx-auto px-4 py-8">
                <div className="flex justify-between items-center mb-6">
                    <h1 className="text-3xl font-bold">Videos</h1>
                    <Link
                        href="/videos/extract"
                        className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
                    >
                        Extract Video
                    </Link>
                </div>

                <form onSubmit={handleSearch} className="mb-6">
                    <input
                        type="text"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        placeholder="Search videos..."
                        className="border rounded px-4 py-2 w-full"
                    />
                </form>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {videos.data.map((video) => (
                        <Link
                            key={video.id}
                            href={`/videos/${video.id}`}
                            className="border rounded-lg p-4 hover:shadow-lg transition"
                        >
                            {video.cover_url && (
                                <img
                                    src={video.cover_url}
                                    alt={video.title}
                                    className="w-full h-48 object-cover rounded mb-4"
                                />
                            )}
                            <h3 className="font-bold text-lg mb-2">
                                {video.title || 'Untitled'}
                            </h3>
                            <p className="text-sm text-gray-600 mb-2">
                                Status: <span className="font-semibold">{video.status}</span>
                            </p>
                            <p className="text-sm text-gray-600">
                                Transcription: <span className="font-semibold">
                                    {video.transcription_status}
                                </span>
                            </p>
                        </Link>
                    ))}
                </div>

                {/* Pagination */}
                {videos.links && (
                    <div className="mt-6 flex justify-center">
                        {videos.links.map((link, index) => (
                            <Link
                                key={index}
                                href={link.url || '#'}
                                className={`px-4 py-2 mx-1 rounded ${
                                    link.active
                                        ? 'bg-blue-500 text-white'
                                        : 'bg-gray-200 text-gray-700'
                                }`}
                                dangerouslySetInnerHTML={{ __html: link.label }}
                            />
                        ))}
                    </div>
                )}
            </div>
        </Layout>
    );
}
```

**File**: `resources/js/Pages/Videos/Show.jsx`

```jsx
import { Head, Link } from '@inertiajs/react';
import Layout from '@/Components/Layout';

export default function Show({ video }) {
    return (
        <Layout>
            <Head title={video.title || 'Video Details'} />
            
            <div className="container mx-auto px-4 py-8">
                <Link href="/videos" className="text-blue-500 hover:underline mb-4">
                    ← Back to Videos
                </Link>

                <div className="bg-white rounded-lg shadow-lg p-6">
                    <h1 className="text-3xl font-bold mb-4">{video.title}</h1>
                    
                    {video.cover_url && (
                        <img
                            src={video.cover_url}
                            alt={video.title}
                            className="w-full max-w-2xl rounded mb-6"
                        />
                    )}

                    <div className="space-y-4">
                        <div>
                            <h2 className="font-bold">Status</h2>
                            <p>{video.status}</p>
                        </div>

                        {video.transcript && (
                            <div>
                                <h2 className="font-bold">Transcript</h2>
                                <p className="whitespace-pre-wrap">{video.transcript}</p>
                            </div>
                        )}

                        {video.ai_summary && (
                            <div>
                                <h2 className="font-bold">AI Summary</h2>
                                <p>{video.ai_summary}</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </Layout>
    );
}
```

### Example Request/Response

**Request** (List):
```
GET /videos?status=success&search=test
```

**Response** (Inertia.js renders React component with data):
- Component receives `videos` prop with paginated data
- Component receives `filters` prop for current filters

### Testing Checklist

- [ ] List page displays all videos
- [ ] Filters work (status, transcription_status, search)
- [ ] Pagination works
- [ ] Detail page shows video information
- [ ] Links navigate correctly
- [ ] Images load correctly
- [ ] Search functionality works

### Completion Notes

**Date Completed**: _______________
**Issues Encountered**: _______________
**Additional Notes**: _______________

---

## 📦 Module 4: Video Download

### Status: ⬜ Not Started | 🟡 In Progress | ✅ Completed

### Old Django Reference

**File**: `backend/downloader/views.py` - `download_video()` function
**File**: `backend/downloader/utils.py` - `download_file()` function

**Django Endpoint**: `POST /api/videos/<id>/download/`

**Django Response**:
```json
{
  "status": "success",
  "message": "Video downloaded successfully"
}
```

### New Laravel Implementation

#### Step 1: Create Service Method

**File**: `app/Services/VideoDownloadService.php`

```php
<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Facades\Log;

class VideoDownloadService
{
    public function download(string $videoUrl, string $filename): ?string
    {
        try {
            $response = Http::timeout(300)->get($videoUrl);
            
            if ($response->successful()) {
                $path = 'videos/' . $filename;
                Storage::disk('public')->put($path, $response->body());
                return $path;
            }
        } catch (\Exception $e) {
            Log::error('Video download error: ' . $e->getMessage());
        }

        return null;
    }
}
```

#### Step 2: Create Controller Method

**File**: `app/Http/Controllers/VideoController.php`

```php
public function download(VideoDownload $video)
{
    if (!$video->video_url) {
        return back()->withErrors(['error' => 'No video URL found']);
    }

    $service = app(VideoDownloadService::class);
    $filename = ($video->video_id ?? 'video') . '_' . $video->id . '.mp4';
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
```

#### Step 3: Add Route

**File**: `routes/web.php`

```php
Route::post('/videos/{video}/download', [VideoController::class, 'download'])
    ->name('videos.download');
```

#### Step 4: Add Frontend Button

**File**: `resources/js/Pages/Videos/Show.jsx`

```jsx
import { router } from '@inertiajs/react';

const handleDownload = () => {
    router.post(`/videos/${video.id}/download`, {}, {
        preserveScroll: true,
    });
};

// In JSX:
{!video.is_downloaded && (
    <button
        onClick={handleDownload}
        className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600"
    >
        Download Video
    </button>
)}
```

### Testing Checklist

- [ ] Service downloads video file
- [ ] File is saved to storage
- [ ] Model is updated correctly
- [ ] Frontend button triggers download
- [ ] Success message is shown
- [ ] Error handling works

### Completion Notes

**Date Completed**: _______________
**Issues Encountered**: _______________
**Additional Notes**: _______________

---

## 📦 Module 5: Transcription (Whisper + NCA + Visual Frame Analysis)

### Status: ⬜ Not Started | 🟡 In Progress | ✅ Completed

### Workflow Overview

1. **Transcription**: Use Whisper (local) or NCA API
2. **Visual Analysis** (Optional): Extract and analyze video frames
3. **AI Optimization**: Compare transcript + visual data to optimize response
4. **Clean Script Generation**: Generate clean script for TTS

### Old Django Reference

**File**: `backend/downloader/views.py` - `transcribe_video_view()`
**File**: `backend/downloader/utils.py` - `transcribe_video()`
**File**: `backend/downloader/nca_toolkit_client.py`

**Django Endpoint**: `POST /api/videos/<id>/transcribe/`

**Django Response**:
```json
{
  "status": "success",
  "message": "Transcription completed",
  "transcript": "Full transcript text...",
  "transcript_hindi": "Hindi translation...",
  "language": "zh"
}
```

### New Laravel Implementation

#### Step 1: Create Transcription Service

**File**: `app/Services/TranscriptionService.php`

```php
<?php

namespace App\Services;

use App\Models\VideoDownload;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Facades\Log;

class TranscriptionService
{
    private string $ncaApiUrl;
    private string $ncaApiKey;
    private bool $ncaEnabled;

    public function __construct()
    {
        $this->ncaApiUrl = config('services.nca.api_url');
        $this->ncaApiKey = config('services.nca.api_key');
        $this->ncaEnabled = config('services.nca.enabled', false);
    }

    /**
     * Transcribe video using Whisper or NCA API
     * Optionally extract visual frames for analysis
     */
    public function transcribe(VideoDownload $video, bool $extractFrames = false): array
    {
        if (!$video->local_file || !Storage::disk('public')->exists($video->local_file)) {
            return [
                'status' => 'error',
                'error' => 'Video file not found',
            ];
        }

        $transcriptResult = null;
        $visualFrames = null;

        // Step 1: Try NCA API first (faster)
        if ($this->ncaEnabled) {
            $transcriptResult = $this->transcribeViaNCA($video);
        }

        // Step 2: Fallback to local Whisper if NCA fails
        if (!$transcriptResult || $transcriptResult['status'] !== 'success') {
            $transcriptResult = $this->transcribeViaWhisper($video);
        }

        // Step 3: Extract visual frames (optional)
        if ($extractFrames && $transcriptResult['status'] === 'success') {
            $visualFrames = $this->extractVisualFrames($video);
        }

        return [
            'status' => $transcriptResult['status'],
            'text' => $transcriptResult['text'] ?? '',
            'language' => $transcriptResult['language'] ?? 'auto',
            'visual_frames' => $visualFrames, // Optional: frame analysis data
        ];
    }

    private function transcribeViaNCA(VideoDownload $video): array
    {
        try {
            $filePath = Storage::disk('public')->path($video->local_file);
            
            $response = Http::timeout(600)
                ->withHeaders([
                    'Authorization' => 'Bearer ' . $this->ncaApiKey,
                ])
                ->attach('file', file_get_contents($filePath), basename($filePath))
                ->post($this->ncaApiUrl . '/v1/toolkit/transcribe');

            if ($response->successful()) {
                $data = $response->json();
                
                return [
                    'status' => 'success',
                    'text' => $data['transcript'] ?? '',
                    'language' => $data['language'] ?? 'auto',
                ];
            }
        } catch (\Exception $e) {
            Log::error('NCA transcription error: ' . $e->getMessage());
        }

        return ['status' => 'error', 'error' => 'NCA API failed'];
    }

    private function transcribeViaWhisper(VideoDownload $video): array
    {
        try {
            // Option 1: Use local Whisper installation
            $filePath = Storage::disk('public')->path($video->local_file);
            
            // Run Whisper command (requires Whisper installed)
            $command = "whisper \"{$filePath}\" --language auto --output_format txt --output_dir " . storage_path('app/temp');
            exec($command, $output, $returnCode);
            
            if ($returnCode === 0) {
                $txtFile = storage_path('app/temp/' . basename($filePath, '.mp4') . '.txt');
                if (file_exists($txtFile)) {
                    $text = file_get_contents($txtFile);
                    unlink($txtFile); // Clean up
                    
                    return [
                        'status' => 'success',
                        'text' => $text,
                        'language' => 'auto', // Whisper detects automatically
                    ];
                }
            }
            
            // Option 2: Use Whisper API (if available)
            // return $this->transcribeViaWhisperAPI($video);
            
        } catch (\Exception $e) {
            Log::error('Whisper transcription error: ' . $e->getMessage());
        }

        return [
            'status' => 'error',
            'error' => 'Whisper transcription failed',
        ];
    }

    /**
     * Extract visual frames from video for analysis (optional)
     */
    private function extractVisualFrames(VideoDownload $video): ?array
    {
        try {
            $filePath = Storage::disk('public')->path($video->local_file);
            
            // Use ffmpeg to extract frames at intervals
            // Extract 1 frame per 5 seconds
            $outputDir = storage_path('app/temp/frames_' . $video->id);
            if (!is_dir($outputDir)) {
                mkdir($outputDir, 0755, true);
            }
            
            $command = sprintf(
                'ffmpeg -i "%s" -vf "fps=1/5" "%s/frame_%%03d.jpg" -y',
                $filePath,
                $outputDir
            );
            
            exec($command, $output, $returnCode);
            
            if ($returnCode === 0) {
                $frames = [];
                $frameFiles = glob($outputDir . '/frame_*.jpg');
                
                foreach ($frameFiles as $frameFile) {
                    // Optionally analyze frame with vision AI
                    $frames[] = [
                        'path' => $frameFile,
                        'timestamp' => $this->extractTimestampFromFilename($frameFile),
                        // 'analysis' => $this->analyzeFrame($frameFile), // Optional: AI vision analysis
                    ];
                }
                
                return $frames;
            }
        } catch (\Exception $e) {
            Log::error('Frame extraction error: ' . $e->getMessage());
        }

        return null;
    }

    private function extractTimestampFromFilename(string $filename): float
    {
        // Extract timestamp from frame filename
        // frame_001.jpg = 5 seconds, frame_002.jpg = 10 seconds, etc.
        if (preg_match('/frame_(\d+)\.jpg/', $filename, $matches)) {
            return (int)$matches[1] * 5; // 5 seconds per frame
        }
        return 0;
    }
}
```

#### Step 2: Create Visual Analysis Service (Optional)

**File**: `app/Services/VisualAnalysisService.php`

```php
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
                Log::error('Frame analysis error: ' . $e->getMessage());
            }
        }
        
        return $analysis;
    }

    private function analyzeFrameWithGemini(string $framePath): array
    {
        $apiKey = config('services.gemini.api_key');
        $imageData = base64_encode(file_get_contents($framePath));
        
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
                                ]
                            ]
                        ]
                    ]
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
```

#### Step 3: Create AI Optimization Service

**File**: `app/Services/AIOptimizationService.php`

```php
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
        
        // Build prompt with transcript and visual context
        $visualContext = $this->buildVisualContext($visualAnalysis);
        
        $prompt = "You are analyzing a video transcript along with visual frame descriptions.\n\n" .
                  "Transcript:\n{$transcript}\n\n" .
                  "Visual Context (from video frames):\n{$visualContext}\n\n" .
                  "Please:\n" .
                  "1. Compare the transcript with visual context\n" .
                  "2. Identify any discrepancies or missing information\n" .
                  "3. Optimize the transcript to include visual context where relevant\n" .
                  "4. Generate a clean, accurate, and contextually rich transcript\n" .
                  "5. Remove filler words, repetitions, and improve clarity\n\n" .
                  "Return only the optimized transcript text.";

        try {
            $response = Http::timeout(60)
                ->post("https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={$apiKey}", [
                    'contents' => [
                        [
                            'parts' => [
                                ['text' => $prompt]
                            ]
                        ]
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
            Log::error('AI optimization error: ' . $e->getMessage());
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
                "[%ds] %s - Objects: %s",
                $analysis['timestamp'],
                $analysis['description'],
                implode(', ', $analysis['objects'])
            );
        }
        return implode("\n", $context);
    }
}
```

#### Step 4: Create Script Generation Service

**File**: `app/Services/ScriptGenerationService.php`

```php
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
        
        $prompt = "Convert this transcript into a clean script optimized for Text-to-Speech synthesis.\n\n" .
                  "Requirements:\n" .
                  "1. Remove all timestamps and timestamps markers\n" .
                  "2. Remove filler words (um, uh, like, etc.)\n" .
                  "3. Fix grammar and sentence structure\n" .
                  "4. Break into natural speech segments\n" .
                  "5. Ensure smooth flow for TTS reading\n" .
                  "6. Translate to {$targetLanguage} if needed\n\n" .
                  "Transcript:\n{$optimizedTranscript}\n\n" .
                  "Return only the clean script text, ready for TTS.";

        try {
            $response = Http::timeout(60)
                ->post("https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={$apiKey}", [
                    'contents' => [
                        [
                            'parts' => [
                                ['text' => $prompt]
                            ]
                        ]
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
            Log::error('Script generation error: ' . $e->getMessage());
        }

        return [
            'status' => 'error',
            'clean_script' => $optimizedTranscript, // Fallback
        ];
    }
}
```

#### Step 5: Create Job for Background Processing

```bash
php artisan make:job TranscribeVideoJob
```

**File**: `app/Jobs/TranscribeVideoJob.php`

```php
<?php

namespace App\Jobs;

use App\Models\VideoDownload;
use App\Services\TranscriptionService;
use App\Services\VisualAnalysisService;
use App\Services\AIOptimizationService;
use App\Services\ScriptGenerationService;
use App\Services\TranslationService;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;

class TranscribeVideoJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public function __construct(
        public int $videoId,
        public bool $extractFrames = false
    ) {}

    public function handle(
        TranscriptionService $transcriptionService,
        VisualAnalysisService $visualAnalysisService,
        AIOptimizationService $aiOptimizationService,
        ScriptGenerationService $scriptGenerationService,
        TranslationService $translationService
    ): void {
        $video = VideoDownload::findOrFail($this->videoId);

        $video->update([
            'transcription_status' => 'transcribing',
            'transcript_started_at' => now(),
        ]);

        // Step 1: Transcribe (with optional frame extraction)
        $result = $transcriptionService->transcribe($video, $this->extractFrames);

        if ($result['status'] !== 'success') {
            $video->update([
                'transcription_status' => 'failed',
                'transcript_error_message' => $result['error'] ?? 'Transcription failed',
            ]);
            return;
        }

        $originalTranscript = $result['text'];
        $optimizedTranscript = $originalTranscript;
        $cleanScript = $originalTranscript;

        // Step 2: Visual Analysis (if frames extracted)
        $visualAnalysis = null;
        if (!empty($result['visual_frames'])) {
            $visualAnalysis = $visualAnalysisService->analyzeFrames(
                $result['visual_frames'],
                $originalTranscript
            );
        }

        // Step 3: AI Optimization (compare transcript + visual data)
        if ($visualAnalysis) {
            $optimizationResult = $aiOptimizationService->optimizeTranscript(
                $originalTranscript,
                $visualAnalysis
            );
            if ($optimizationResult['status'] === 'success') {
                $optimizedTranscript = $optimizationResult['optimized_transcript'];
            }
        }

        // Step 4: Generate clean script for TTS
        $scriptResult = $scriptGenerationService->generateCleanScript($optimizedTranscript, 'hi');
        if ($scriptResult['status'] === 'success') {
            $cleanScript = $scriptResult['clean_script'];
        }

        // Step 5: Save all results
        $video->update([
            'transcription_status' => 'transcribed',
            'transcript' => $originalTranscript,
            'transcript_optimized' => $optimizedTranscript, // Add this field to migration
            'transcript_clean_script' => $cleanScript, // Add this field to migration
            'transcript_language' => $result['language'],
            'transcript_processed_at' => now(),
            'transcript_hindi' => $translationService->translate($cleanScript, 'hi'),
            'visual_analysis' => $visualAnalysis ? json_encode($visualAnalysis) : null, // Add this field
        ]);
    }
}
```

#### Step 3: Create Controller Method

**File**: `app/Http/Controllers/VideoController.php`

```php
public function transcribe(VideoDownload $video)
{
    if ($video->transcription_status === 'transcribing') {
        return back()->withErrors(['error' => 'Transcription already in progress']);
    }

    TranscribeVideoJob::dispatch($video->id);

    return back()->with('message', 'Transcription started');
}
```

#### Step 4: Add Route

**File**: `routes/web.php`

```php
Route::post('/videos/{video}/transcribe', [VideoController::class, 'transcribe'])
    ->name('videos.transcribe');
```

### Testing Checklist

- [ ] Service connects to NCA API
- [ ] Service handles file upload correctly
- [ ] Service processes response correctly
- [ ] Job updates video status
- [ ] Hindi translation works
- [ ] Error handling works
- [ ] Frontend can trigger transcription

### Completion Notes

**Date Completed**: _______________
**Issues Encountered**: _______________
**Additional Notes**: _______________

---

## 📦 Module 6: AI Processing

### Status: ⬜ Not Started | 🟡 In Progress | ✅ Completed

### Old Django Reference

**File**: `backend/downloader/views.py` - `process_ai_view()`
**File**: `backend/downloader/utils.py` - `process_video_with_ai()`

**Django Endpoint**: `POST /api/videos/<id>/process_ai/`

**Django Response**:
```json
{
  "status": "success",
  "message": "AI processing completed",
  "summary": "AI-generated summary...",
  "tags": "tag1, tag2, tag3"
}
```

### New Laravel Implementation

#### Step 1: Create AI Service

**File**: `app/Services/AIService.php`

```php
<?php

namespace App\Services;

use App\Models\AIProviderSettings;
use App\Models\VideoDownload;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class AIService
{
    public function processVideo(VideoDownload $video): array
    {
        $settings = AIProviderSettings::getSettings();

        if ($settings->provider === 'gemini') {
            return $this->processWithGemini($video, $settings->api_key);
        }

        return [
            'status' => 'error',
            'error' => 'Unsupported AI provider',
        ];
    }

    private function processWithGemini(VideoDownload $video, string $apiKey): array
    {
        try {
            $prompt = $this->buildPrompt($video);
            
            $response = Http::timeout(60)
                ->withHeaders([
                    'Content-Type' => 'application/json',
                ])
                ->post("https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={$apiKey}", [
                    'contents' => [
                        [
                            'parts' => [
                                ['text' => $prompt]
                            ]
                        ]
                    ],
                ]);

            if ($response->successful()) {
                $data = $response->json();
                $text = $data['candidates'][0]['content']['parts'][0]['text'] ?? '';
                
                return $this->parseAIResponse($text);
            }
        } catch (\Exception $e) {
            Log::error('Gemini AI error: ' . $e->getMessage());
        }

        return [
            'status' => 'error',
            'error' => 'AI processing failed',
        ];
    }

    private function buildPrompt(VideoDownload $video): string
    {
        $transcript = $video->transcript_optimized ?? $video->transcript ?? 'No transcript available';
        $visualContext = '';
        
        // Include visual analysis if available
        if ($video->visual_analysis) {
            $visualData = json_decode($video->visual_analysis, true);
            if ($visualData) {
                $visualContext = "\n\nVisual Context from Video Frames:\n";
                foreach ($visualData as $analysis) {
                    $visualContext .= sprintf(
                        "[%ds] %s - Objects: %s\n",
                        $analysis['timestamp'] ?? 0,
                        $analysis['description'] ?? '',
                        implode(', ', $analysis['objects'] ?? [])
                    );
                }
            }
        }
        
        return "Analyze this video transcript and visual context to provide:\n\n" .
               "1. A concise summary (2-3 sentences) that incorporates both audio and visual information\n" .
               "2. 5-10 relevant tags (comma-separated) based on both transcript and visual content\n\n" .
               "Transcript:\n{$transcript}{$visualContext}";
    }

    private function parseAIResponse(string $text): array
    {
        $lines = explode("\n", $text);
        $summary = '';
        $tags = [];

        foreach ($lines as $line) {
            if (stripos($line, 'summary') !== false || stripos($line, 'tags') === false) {
                $summary .= $line . "\n";
            } elseif (stripos($line, 'tags') !== false) {
                $tagLine = str_replace(['Tags:', 'tags:', '-'], '', $line);
                $tags = array_map('trim', explode(',', $tagLine));
            }
        }

        return [
            'status' => 'success',
            'summary' => trim($summary),
            'tags' => array_filter($tags),
        ];
    }
}
```

#### Step 2: Create Job

```bash
php artisan make:job ProcessAIJob
```

**File**: `app/Jobs/ProcessAIJob.php`

```php
<?php

namespace App\Jobs;

use App\Models\VideoDownload;
use App\Services\AIService;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;

class ProcessAIJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public function __construct(
        public int $videoId
    ) {}

    public function handle(AIService $aiService): void
    {
        $video = VideoDownload::findOrFail($this->videoId);

        $video->update(['ai_processing_status' => 'processing']);

        $result = $aiService->processVideo($video);

        if ($result['status'] === 'success') {
            $video->update([
                'ai_processing_status' => 'processed',
                'ai_summary' => $result['summary'],
                'ai_tags' => implode(',', $result['tags']),
                'ai_processed_at' => now(),
            ]);
        } else {
            $video->update([
                'ai_processing_status' => 'failed',
                'ai_error_message' => $result['error'] ?? 'AI processing failed',
            ]);
        }
    }
}
```

#### Step 3: Create Controller Method

**File**: `app/Http/Controllers/VideoController.php`

```php
public function processAI(VideoDownload $video)
{
    if ($video->ai_processing_status === 'processing') {
        return back()->withErrors(['error' => 'AI processing already in progress']);
    }

    ProcessAIJob::dispatch($video->id);

    return back()->with('message', 'AI processing started');
}
```

### Testing Checklist

- [ ] Service connects to Gemini API
- [ ] Service builds prompt correctly
- [ ] Service parses response correctly
- [ ] Job updates video status
- [ ] Summary and tags are saved
- [ ] Error handling works

### Completion Notes

**Date Completed**: _______________
**Issues Encountered**: _______________
**Additional Notes**: _______________

---

## 📦 Module 7: TTS Synthesis (Google TTS)

### Status: ⬜ Not Started | 🟡 In Progress | ✅ Completed

### Workflow Overview

1. **Use Clean Script**: Get the clean script generated in Module 5
2. **Google TTS**: Use Google Cloud Text-to-Speech API
3. **Save Audio**: Save synthesized audio file
4. **Match Duration**: Adjust audio duration to match video if needed

### Old Django Reference

**File**: `backend/downloader/views.py` - `synthesize_audio_view()`
**File**: `legacy/root_debris/downloader/gemini_tts_service.py`

**Django Endpoint**: `POST /api/videos/<id>/synthesize/`

**Django Response**:
```json
{
  "status": "success",
  "message": "Audio synthesis completed",
  "audio_url": "/media/synthesized_audio/tts_xxx.mp3"
}
```

### New Laravel Implementation

#### Step 1: Install Google Cloud TTS Package

```bash
composer require google/cloud-text-to-speech
```

#### Step 2: Create Google TTS Service

**File**: `app/Services/GoogleTTSService.php`

```php
<?php

namespace App\Services;

use Google\Cloud\TextToSpeech\V1\AudioConfig;
use Google\Cloud\TextToSpeech\V1\AudioEncoding;
use Google\Cloud\TextToSpeech\V1\SynthesisInput;
use Google\Cloud\TextToSpeech\V1\TextToSpeechClient;
use Google\Cloud\TextToSpeech\V1\VoiceSelectionParams;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Facades\Log;

class GoogleTTSService
{
    private TextToSpeechClient $client;
    private string $credentialsPath;

    public function __construct()
    {
        $this->credentialsPath = config('services.google_tts.credentials_path');
        
        // Initialize Google TTS client
        $this->client = new TextToSpeechClient([
            'credentials' => $this->credentialsPath,
        ]);
    }

    /**
     * Synthesize speech from text using Google TTS
     * 
     * @param string $text Text to synthesize
     * @param string $languageCode Language code (e.g., 'hi-IN', 'en-US')
     * @param string $voiceName Voice name (e.g., 'hi-IN-Standard-A', 'en-US-Standard-B')
     * @param string $outputPath Path to save audio file
     * @param int|null $targetDuration Target duration in seconds (for speed adjustment)
     * @return bool Success status
     */
    public function synthesize(
        string $text,
        string $languageCode = 'hi-IN',
        string $voiceName = 'hi-IN-Standard-A',
        string $outputPath = null,
        ?int $targetDuration = null
    ): bool {
        try {
            // Split text into chunks if too long (Google TTS has limits)
            $chunks = $this->splitTextIntoChunks($text, 5000); // 5000 characters per chunk
            
            $audioData = '';
            
            foreach ($chunks as $chunk) {
                // Create synthesis input
                $input = new SynthesisInput();
                $input->setText($chunk);
                
                // Configure voice
                $voice = new VoiceSelectionParams();
                $voice->setLanguageCode($languageCode);
                $voice->setName($voiceName);
                
                // Configure audio
                $audioConfig = new AudioConfig();
                $audioConfig->setAudioEncoding(AudioEncoding::MP3);
                $audioConfig->setSpeakingRate(1.0); // Normal speed
                $audioConfig->setPitch(0.0); // Normal pitch
                
                // Perform synthesis
                $response = $this->client->synthesizeSpeech($input, $voice, $audioConfig);
                $audioData .= $response->getAudioContent();
            }
            
            // Save audio file
            if ($outputPath) {
                Storage::disk('public')->put($outputPath, $audioData);
                
                // Adjust duration if needed
                if ($targetDuration) {
                    $this->adjustAudioDuration($outputPath, $targetDuration);
                }
                
                return true;
            }
            
            return false;
        } catch (\Exception $e) {
            Log::error('Google TTS error: ' . $e->getMessage());
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
            if (strlen($currentChunk . $sentence) > $maxLength) {
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
            $tempPath = storage_path('app/temp/' . basename($audioPath));
            
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
            Log::error('Audio duration adjustment error: ' . $e->getMessage());
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
            return $duration ? (float)$duration : null;
        } catch (\Exception $e) {
            return null;
        }
    }

    /**
     * Get available voices for a language
     */
    public function getAvailableVoices(string $languageCode = 'hi-IN'): array
    {
        try {
            $voices = $this->client->listVoices(['languageCode' => $languageCode]);
            $voiceList = [];
            
            foreach ($voices->getVoices() as $voice) {
                foreach ($voice->getName() as $name) {
                    $voiceList[] = [
                        'name' => $name,
                        'language_code' => $voice->getLanguageCodes()[0] ?? $languageCode,
                        'gender' => $voice->getSsmlGender(),
                        'natural_sample_rate' => $voice->getNaturalSampleRateHertz(),
                    ];
                }
            }
            
            return $voiceList;
        } catch (\Exception $e) {
            Log::error('Get voices error: ' . $e->getMessage());
            return [];
        }
    }
}
```

#### Step 3: Create Job for TTS Synthesis

```bash
php artisan make:job SynthesizeAudioJob
```

**File**: `app/Jobs/SynthesizeAudioJob.php`

```php
<?php

namespace App\Jobs;

use App\Models\VideoDownload;
use App\Services\GoogleTTSService;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Storage;

class SynthesizeAudioJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public function __construct(
        public int $videoId,
        public string $languageCode = 'hi-IN',
        public string $voiceName = 'hi-IN-Standard-A'
    ) {}

    public function handle(GoogleTTSService $ttsService): void
    {
        $video = VideoDownload::findOrFail($this->videoId);

        // Check if clean script exists
        if (!$video->transcript_clean_script) {
            $video->update([
                'step_tts_synthesis_status' => 'failed',
                'synthesis_error' => 'Clean script not found. Please generate script first.',
            ]);
            return;
        }

        $video->update([
            'step_tts_synthesis_status' => 'processing',
        ]);

        // Generate output path
        $filename = 'synthesized_audio/tts_' . ($video->video_id ?? $video->id) . '_' . time() . '.mp3';
        $outputPath = $filename;

        // Synthesize audio
        $success = $ttsService->synthesize(
            $video->transcript_clean_script,
            $this->languageCode,
            $this->voiceName,
            $outputPath,
            $video->duration // Target duration to match video
        );

        if ($success) {
            $video->update([
                'step_tts_synthesis_status' => 'completed',
                'synthesized_audio_path' => $outputPath, // Add this field to migration
                'synthesized_at' => now(),
            ]);
        } else {
            $video->update([
                'step_tts_synthesis_status' => 'failed',
                'synthesis_error' => 'TTS synthesis failed',
            ]);
        }
    }
}
```

#### Step 4: Create Controller Method

**File**: `app/Http/Controllers/VideoController.php`

```php
public function synthesize(VideoDownload $video, Request $request)
{
    if ($video->step_tts_synthesis_status === 'processing') {
        return back()->withErrors(['error' => 'TTS synthesis already in progress']);
    }

    if (!$video->transcript_clean_script) {
        return back()->withErrors(['error' => 'Clean script not found. Please complete transcription first.']);
    }

    $languageCode = $request->input('language_code', 'hi-IN');
    $voiceName = $request->input('voice_name', 'hi-IN-Standard-A');

    SynthesizeAudioJob::dispatch($video->id, $languageCode, $voiceName);

    return back()->with('message', 'TTS synthesis started');
}
```

#### Step 5: Add Route

**File**: `routes/web.php`

```php
Route::post('/videos/{video}/synthesize', [VideoController::class, 'synthesize'])
    ->name('videos.synthesize');
```

#### Step 6: Add Frontend Button

**File**: `resources/js/Pages/Videos/Show.jsx`

```jsx
import { router } from '@inertiajs/react';

const handleSynthesize = () => {
    router.post(`/videos/${video.id}/synthesize`, {
        language_code: 'hi-IN',
        voice_name: 'hi-IN-Standard-A',
    }, {
        preserveScroll: true,
    });
};

// In JSX:
{video.transcript_clean_script && video.step_tts_synthesis_status !== 'processing' && (
    <button
        onClick={handleSynthesize}
        className="bg-purple-500 text-white px-4 py-2 rounded hover:bg-purple-600"
    >
        Synthesize Audio (Google TTS)
    </button>
)}

{video.synthesized_audio_path && (
    <audio controls className="mt-4">
        <source src={`/storage/${video.synthesized_audio_path}`} type="audio/mpeg" />
    </audio>
)}
```

### Configuration

**File**: `config/services.php`

```php
'google_tts' => [
    'credentials_path' => env('GOOGLE_TTS_CREDENTIALS_PATH'),
],
```

**.env**:
```env
GOOGLE_TTS_CREDENTIALS_PATH=/path/to/google-credentials.json
```

### Example Request/Response

**Request**:
```javascript
router.post('/videos/1/synthesize', {
    language_code: 'hi-IN',
    voice_name: 'hi-IN-Standard-A'
})
```

**Response**:
- Redirects back with success message
- Audio file is generated and saved
- Video model is updated with audio path

### Testing Checklist

- [ ] Google TTS service connects successfully
- [ ] Service handles long text (chunking works)
- [ ] Audio file is generated correctly
- [ ] Audio duration adjustment works
- [ ] File is saved to storage
- [ ] Job processes correctly
- [ ] Frontend can trigger synthesis
- [ ] Audio player displays correctly
- [ ] Error handling works

### Completion Notes

**Date Completed**: _______________
**Issues Encountered**: _______________
**Additional Notes**: _______________

---

## 📦 Module 8: Video Processing

### Status: ⬜ Not Started | 🟡 In Progress | ✅ Completed

### Old Django Reference

**File**: `backend/downloader/pipeline_v2.py`

### New Laravel Implementation

*(Create pipeline service and jobs for video processing)*

### Testing Checklist

- [ ] Video processing works
- [ ] Watermarking works
- [ ] Audio replacement works

### Completion Notes

**Date Completed**: _______________
**Issues Encountered**: _______________
**Additional Notes**: _______________

---

## 📦 Module 9: Settings Management

### Status: ⬜ Not Started | 🟡 In Progress | ✅ Completed

### Old Django Reference

**File**: `backend/downloader/views.py` - `ai_settings()`
**File**: `backend/downloader/models.py` - `AIProviderSettings`

### New Laravel Implementation

*(Create settings controller and pages)*

### Testing Checklist

- [ ] Settings can be saved
- [ ] Settings are retrieved correctly
- [ ] Settings page works

### Completion Notes

**Date Completed**: _______________
**Issues Encountered**: _______________
**Additional Notes**: _______________

---

## 📦 Module 10: Bulk Operations

### Status: ⬜ Not Started | 🟡 In Progress | ✅ Completed

### Old Django Reference

**File**: `backend/downloader/bulk_views.py`

### New Laravel Implementation

*(Create bulk operations controller)*

### Testing Checklist

- [ ] Bulk delete works
- [ ] Bulk operations are efficient

### Completion Notes

**Date Completed**: _______________
**Issues Encountered**: _______________
**Additional Notes**: _______________

---

## 📦 Module 11: Retry Operations

### Status: ⬜ Not Started | 🟡 In Progress | ✅ Completed

### Old Django Reference

**File**: `backend/downloader/retry_views.py`

### New Laravel Implementation

*(Create retry controller methods)*

### Testing Checklist

- [ ] Retry operations work
- [ ] Failed steps can be retried

### Completion Notes

**Date Completed**: _______________
**Issues Encountered**: _______________
**Additional Notes**: _______________

---

## 📦 Module 12: Dashboard & Statistics

### Status: ⬜ Not Started | 🟡 In Progress | ✅ Completed

### Old Django Reference

**File**: `backend/downloader/admin.py` - Dashboard stats

### New Laravel Implementation

**File**: `app/Http/Controllers/DashboardController.php`

```php
<?php

namespace App\Http\Controllers;

use App\Models\VideoDownload;
use Inertia\Inertia;

class DashboardController extends Controller
{
    public function index()
    {
        $stats = [
            'total_videos' => VideoDownload::count(),
            'successful_videos' => VideoDownload::where('status', 'success')->count(),
            'transcribed_videos' => VideoDownload::where('transcription_status', 'transcribed')->count(),
            'ai_processed_videos' => VideoDownload::where('ai_processing_status', 'processed')->count(),
            'recent_videos' => VideoDownload::latest()->take(10)->get(),
        ];

        return Inertia::render('Dashboard', [
            'stats' => $stats,
        ]);
    }
}
```

### Testing Checklist

- [ ] Dashboard displays statistics
- [ ] Recent videos are shown
- [ ] Statistics are accurate

### Completion Notes

**Date Completed**: _______________
**Issues Encountered**: _______________
**Additional Notes**: _______________

---

## 📊 Overall Progress Tracker

| Module | Status | Date Completed | Notes |
|--------|--------|----------------|-------|
| Module 1: Project Setup & Database | ⬜ | | |
| Module 2: Video Extraction | ⬜ | | |
| Module 3: Video Listing & Detail | ⬜ | | |
| Module 4: Video Download | ⬜ | | |
| Module 5: Transcription | ⬜ | | |
| Module 6: AI Processing | ⬜ | | |
| Module 7: TTS Synthesis | ⬜ | | |
| Module 8: Video Processing | ⬜ | | |
| Module 9: Settings Management | ⬜ | | |
| Module 10: Bulk Operations | ⬜ | | |
| Module 11: Retry Operations | ⬜ | | |
| Module 12: Dashboard & Statistics | ⬜ | | |

---

## 🎯 Next Steps

1. Start with **Module 1** and complete it fully
2. Test thoroughly before moving to next module
3. Mark each module as completed when done
4. Document any issues or customizations
5. Continue module by module until all are complete

---

**Happy migrating! 🚀**

