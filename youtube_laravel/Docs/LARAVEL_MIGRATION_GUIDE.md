# Complete Migration Guide: Django → Laravel + Inertia.js + React

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture Comparison](#architecture-comparison)
3. [Project Structure](#project-structure)
4. [Step-by-Step Migration](#step-by-step-migration)
5. [Database Migration](#database-migration)
6. [Backend Migration](#backend-migration)
7. [Frontend Migration](#frontend-migration)
8. [External Services Integration](#external-services-integration)
9. [Background Jobs & Queues](#background-jobs--queues)
10. [File Storage](#file-storage)
11. [Testing & Deployment](#testing--deployment)

---

## 🎯 Project Overview

### Current Stack
- **Backend**: Django (Python) with SQLite
- **Frontend**: React (Vite) with React Router
- **Communication**: REST API (JSON)

### Target Stack
- **Backend**: Laravel (PHP) with MySQL/PostgreSQL
- **Frontend**: React (Vite) with Inertia.js
- **Communication**: Inertia.js (Server-side rendering with React components)

### Key Features to Migrate
1. Video extraction from Xiaohongshu (RedNote)
2. Video transcription (NCA Toolkit API / Whisper)
3. AI processing (Gemini AI - summaries, tags)
4. Translation (Chinese → English/Hindi)
5. TTS synthesis (Gemini TTS, XTTS)
6. Video processing (watermarking, audio replacement)
7. Cloudinary upload
8. Google Sheets sync
9. Background job processing
10. Admin dashboard with statistics

---

## 🏗️ Architecture Comparison

### Django Architecture (Current)
```
Frontend (React) → REST API → Django Views → Models → SQLite
```

### Laravel + Inertia.js Architecture (Target)
```
React Components → Inertia.js → Laravel Controllers → Models → MySQL/PostgreSQL
```

**Key Benefits:**
- ✅ Single codebase (no separate API)
- ✅ Server-side rendering with React
- ✅ Shared validation rules
- ✅ Better SEO
- ✅ Simpler authentication
- ✅ Type safety with TypeScript (optional)

---

## 📁 Project Structure

### Recommended Laravel Project Structure

```
youtubefinal-laravel/
├── app/
│   ├── Console/
│   │   └── Commands/
│   ├── Exceptions/
│   ├── Http/
│   │   ├── Controllers/
│   │   │   ├── VideoController.php
│   │   │   ├── TranscriptionController.php
│   │   │   ├── AIController.php
│   │   │   ├── TTSController.php
│   │   │   ├── SettingsController.php
│   │   │   ├── DashboardController.php
│   │   │   └── BulkOperationController.php
│   │   ├── Middleware/
│   │   ├── Requests/
│   │   │   ├── ExtractVideoRequest.php
│   │   │   ├── TranscribeVideoRequest.php
│   │   │   └── ProcessAIRequest.php
│   │   └── Resources/
│   │       └── VideoResource.php
│   ├── Jobs/
│   │   ├── ExtractVideoJob.php
│   │   ├── TranscribeVideoJob.php
│   │   ├── ProcessAIJob.php
│   │   ├── GenerateScriptJob.php
│   │   ├── SynthesizeAudioJob.php
│   │   ├── ProcessFinalVideoJob.php
│   │   ├── UploadToCloudinaryJob.php
│   │   └── SyncGoogleSheetsJob.php
│   ├── Models/
│   │   ├── VideoDownload.php
│   │   ├── AIProviderSettings.php
│   │   ├── SavedVoice.php
│   │   ├── WatermarkSettings.php
│   │   ├── CloudinarySettings.php
│   │   └── GoogleSheetsSettings.php
│   ├── Services/
│   │   ├── VideoExtractionService.php
│   │   ├── TranscriptionService.php
│   │   ├── AIService.php
│   │   ├── TranslationService.php
│   │   ├── TTSService.php
│   │   ├── VideoProcessingService.php
│   │   ├── CloudinaryService.php
│   │   └── GoogleSheetsService.php
│   └── Pipelines/
│       └── VideoProcessingPipeline.php
├── bootstrap/
├── config/
├── database/
│   ├── migrations/
│   │   ├── 2024_01_01_000001_create_video_downloads_table.php
│   │   ├── 2024_01_01_000002_create_ai_provider_settings_table.php
│   │   ├── 2024_01_01_000003_create_saved_voices_table.php
│   │   └── ...
│   └── seeders/
├── public/
├── resources/
│   ├── js/
│   │   ├── Pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Videos/
│   │   │   │   ├── Index.jsx
│   │   │   │   └── Show.jsx
│   │   │   ├── Settings.jsx
│   │   │   └── VoiceCloning.jsx
│   │   ├── Components/
│   │   │   ├── Layout/
│   │   │   ├── VideoCard.jsx
│   │   │   ├── VideoPlayer.jsx
│   │   │   └── ...
│   │   ├── app.jsx
│   │   └── bootstrap.js
│   └── css/
├── routes/
│   ├── web.php
│   └── channels.php
├── storage/
│   ├── app/
│   │   ├── public/
│   │   │   ├── videos/
│   │   │   ├── synthesized_audio/
│   │   │   └── voices/
│   └── logs/
├── tests/
├── .env
├── composer.json
├── package.json
└── vite.config.js
```

---

## 🚀 Step-by-Step Migration

### Phase 1: Setup Laravel Project

#### 1.1 Install Laravel

```bash
# Install Laravel Installer globally (if not already installed)
composer global require laravel/installer

# Create new Laravel project
laravel new youtubefinal-laravel

cd youtubefinal-laravel
```

> **Important**: When creating a Laravel 12 project, you'll be prompted to select:
> - Frontend provider (React, Vue, etc.)
> - Authentication options
> - Other project configuration options
> 
> **Please handle these prompts yourself** - choose React as the frontend provider and configure authentication and other options as needed for your project.

**After handling the project creation prompts, if you need additional authentication setup:**

```bash
# Install Laravel Breeze (if not already configured during project creation)
composer require laravel/breeze --dev
php artisan breeze:install react
npm install
npm run build
php artisan migrate
```

**What Laravel Breeze Provides:**
- ✅ Complete authentication system (Login, Register, Password Reset, Email Verification)
- ✅ React + Inertia.js authentication pages pre-configured
- ✅ User model and migration ready to use
- ✅ Authentication middleware and routes
- ✅ Layout components (Navigation, Guest Layout, Authenticated Layout)
- ✅ Inertia.js already configured and working

**After Breeze Installation:**
- You'll have working authentication pages at `/login`, `/register`, etc.
- User model is ready at `app/Models/User.php`
- Authentication middleware is configured
- You can start building your app features immediately

> **Note**: Breeze automatically installs and configures Inertia.js and React, so you can skip manual Inertia.js setup if you use Breeze. If you need additional Inertia.js configuration, continue with the steps below.
```

#### 1.2 Configure Inertia.js (if needed)

If Breeze didn't fully configure Inertia.js or you need additional setup:

**resources/js/app.jsx**
```jsx
import './bootstrap';
import '../css/app.css';

import { createRoot } from 'react-dom/client';
import { createInertiaApp } from '@inertiajs/react';
import { resolvePageComponent } from 'laravel-vite-plugin/inertia-helpers';

const appName = import.meta.env.VITE_APP_NAME || 'Laravel';

createInertiaApp({
    title: (title) => `${title} - ${appName}`,
    resolve: (name) => resolvePageComponent(`./Pages/${name}.jsx`, import.meta.glob('./Pages/**/*.jsx')),
    setup({ el, App, props }) {
        const root = createRoot(el);
        root.render(<App {...props} />);
    },
    progress: {
        color: '#4B5563',
    },
});
```

**resources/js/bootstrap.js**
```javascript
import axios from 'axios';
window.axios = axios;
window.axios.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';
```

**app/Http/Middleware/HandleInertiaRequests.php**
```php
<?php

namespace App\Http\Middleware;

use Illuminate\Http\Request;
use Inertia\Middleware;

class HandleInertiaRequests extends Middleware
{
    protected $rootView = 'app';

    public function share(Request $request): array
    {
        return array_merge(parent::share($request), [
            'auth' => [
                'user' => $request->user(),
            ],
            'flash' => [
                'message' => fn () => $request->session()->get('message'),
                'error' => fn () => $request->session()->get('error'),
            ],
        ]);
    }
}
```

**vite.config.js**
```javascript
import { defineConfig } from 'vite';
import laravel from 'laravel-vite-plugin';
import react from '@vitejs/plugin-react';

export default defineConfig({
    plugins: [
        laravel({
            input: 'resources/js/app.jsx',
            refresh: true,
        }),
        react(),
    ],
});
```

#### 1.3 Create Inertia Root Template

**resources/views/app.blade.php**
```blade
<!DOCTYPE html>
<html lang="{{ str_replace('_', '-', app()->getLocale()) }}">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title inertia>{{ config('app.name', 'Laravel') }}</title>
        @routes
        @viteReactRefresh
        @vite(['resources/css/app.css', 'resources/js/app.jsx'])
        @inertiaHead
    </head>
    <body class="font-sans antialiased">
        @inertia
    </body>
</html>
```

---

### Phase 2: Database Migration

#### 2.1 Create Migrations

**database/migrations/2024_01_01_000001_create_video_downloads_table.php**
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

**database/migrations/2024_01_01_000002_create_ai_provider_settings_table.php**
```php
<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('ai_provider_settings', function (Blueprint $table) {
            $table->id();
            $table->enum('provider', ['gemini', 'openai', 'anthropic'])->default('gemini');
            $table->string('api_key', 255)->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('ai_provider_settings');
    }
};
```

**database/migrations/2024_01_01_000003_create_saved_voices_table.php**
```php
<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('saved_voices', function (Blueprint $table) {
            $table->id();
            $table->string('name', 255);
            $table->string('file');
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('saved_voices');
    }
};
```

#### 2.2 Run Migrations

```bash
php artisan migrate
```

---

### Phase 3: Model Migration

#### 3.1 Create Models

**app/Models/VideoDownload.php**
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

    // Accessors
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

**app/Models/AIProviderSettings.php**
```php
<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class AIProviderSettings extends Model
{
    protected $table = 'ai_provider_settings';
    
    protected $fillable = [
        'provider',
        'api_key',
    ];

    protected $casts = [
        'provider' => 'string',
    ];

    public static function getSettings()
    {
        return static::first() ?? static::create([
            'provider' => 'gemini',
            'api_key' => '',
        ]);
    }
}
```

**app/Models/SavedVoice.php**
```php
<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class SavedVoice extends Model
{
    protected $fillable = [
        'name',
        'file',
    ];
}
```

---

### Phase 4: Service Layer Migration

#### 4.1 Video Extraction Service

**app/Services/VideoExtractionService.php**
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

        // Try yt-dlp
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

            if ($data['code'] === '0000' && isset($data['data'])) {
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
        // Use PHP's exec or a Laravel package for yt-dlp
        // For now, return null - implement based on your needs
        return null;
    }

    private function extractViaRequests(string $url): ?array
    {
        // Implement direct HTTP requests extraction
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

#### 4.2 Translation Service

**app/Services/TranslationService.php**
```php
<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class TranslationService
{
    public function translate(string $text, string $target = 'en'): string
    {
        if (empty($text)) {
            return '';
        }

        try {
            // Using Google Translate API (you can use any translation service)
            // For production, use a proper translation package like:
            // composer require stichoza/google-translate-php
            
            $response = Http::post('https://translate.googleapis.com/translate_a/single', [
                'client' => 'gtx',
                'sl' => 'auto',
                'tl' => $target,
                'dt' => 't',
                'q' => $text,
            ]);

            $result = $response->json();
            
            if (isset($result[0][0][0])) {
                return $result[0][0][0];
            }
        } catch (\Exception $e) {
            Log::error('Translation error: ' . $e->getMessage());
        }

        return $text;
    }
}
```

#### 4.3 Transcription Service

**app/Services/TranscriptionService.php**
```php
<?php

namespace App\Services;

use App\Models\VideoDownload;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Storage;

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

    public function transcribe(VideoDownload $video): array
    {
        if (!$video->local_file || !Storage::exists($video->local_file)) {
            return [
                'status' => 'error',
                'error' => 'Video file not found',
            ];
        }

        // Try NCA API first
        if ($this->ncaEnabled) {
            $result = $this->transcribeViaNCA($video);
            if ($result['status'] === 'success') {
                return $result;
            }
        }

        // Fallback to local Whisper (if available)
        return $this->transcribeViaWhisper($video);
    }

    private function transcribeViaNCA(VideoDownload $video): array
    {
        try {
            $filePath = Storage::path($video->local_file);
            
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
        // Implement local Whisper transcription
        // This would require installing Whisper or using a package
        return [
            'status' => 'error',
            'error' => 'Local Whisper not implemented',
        ];
    }
}
```

#### 4.4 AI Service

**app/Services/AIService.php**
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

        // Add other providers (OpenAI, Anthropic) as needed
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
        return "Analyze this video transcript and provide:\n\n" .
               "1. A concise summary (2-3 sentences)\n" .
               "2. 5-10 relevant tags (comma-separated)\n\n" .
               "Transcript:\n" . ($video->transcript ?? 'No transcript available');
    }

    private function parseAIResponse(string $text): array
    {
        // Parse AI response to extract summary and tags
        // This is a simplified version - adjust based on your AI response format
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

---

### Phase 5: Controller Migration

#### 5.1 Video Controller

**app/Http/Controllers/VideoController.php**
```php
<?php

namespace App\Http\Controllers;

use App\Models\VideoDownload;
use App\Services\VideoExtractionService;
use App\Services\TranslationService;
use App\Jobs\ProcessVideoPipeline;
use Illuminate\Http\Request;
use Inertia\Inertia;
use Inertia\Response;

class VideoController extends Controller
{
    public function __construct(
        private VideoExtractionService $extractionService,
        private TranslationService $translationService
    ) {}

    public function index(Request $request): Response
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

    public function show(VideoDownload $video): Response
    {
        return Inertia::render('Videos/Show', [
            'video' => $video,
        ]);
    }

    public function extract(Request $request)
    {
        $request->validate([
            'url' => 'required|url',
        ]);

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

    public function destroy(VideoDownload $video)
    {
        // Delete associated files
        if ($video->local_file) {
            \Storage::delete($video->local_file);
        }

        $video->delete();

        return redirect()->route('videos.index')
            ->with('message', 'Video deleted successfully');
    }
}
```

#### 5.2 Dashboard Controller

**app/Http/Controllers/DashboardController.php**
```php
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

---

### Phase 6: Background Jobs

#### 6.1 Video Processing Pipeline Job

**app/Jobs/ProcessVideoPipeline.php**
```php
<?php

namespace App\Jobs;

use App\Models\VideoDownload;
use App\Services\TranscriptionService;
use App\Services\AIService;
use App\Services\TranslationService;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Log;

class ProcessVideoPipeline implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public function __construct(
        public int $videoId
    ) {}

    public function handle(
        TranscriptionService $transcriptionService,
        AIService $aiService,
        TranslationService $translationService
    ): void {
        $video = VideoDownload::findOrFail($this->videoId);

        try {
            // Step 1: Download video (if not already downloaded)
            if (!$video->is_downloaded && $video->video_url) {
                $this->downloadVideo($video);
            }

            // Step 2: Transcribe
            if ($video->transcription_status !== 'transcribed') {
                $this->transcribeVideo($video, $transcriptionService, $translationService);
            }

            // Step 3: AI Processing
            if ($video->ai_processing_status !== 'processed') {
                $this->processAI($video, $aiService);
            }

            // Step 4: Generate Hindi script (if needed)
            // Step 5: TTS Synthesis
            // Step 6: Final video processing
            // Step 7: Upload to Cloudinary
            // Step 8: Sync to Google Sheets

        } catch (\Exception $e) {
            Log::error("Pipeline error for video {$this->videoId}: " . $e->getMessage());
            $video->update([
                'status' => 'failed',
                'error_message' => $e->getMessage(),
            ]);
        }
    }

    private function downloadVideo(VideoDownload $video): void
    {
        // Implement video download logic
        $video->update(['is_downloaded' => true]);
    }

    private function transcribeVideo(
        VideoDownload $video,
        TranscriptionService $transcriptionService,
        TranslationService $translationService
    ): void {
        $video->update([
            'transcription_status' => 'transcribing',
            'transcript_started_at' => now(),
        ]);

        $result = $transcriptionService->transcribe($video);

        if ($result['status'] === 'success') {
            $video->update([
                'transcription_status' => 'transcribed',
                'transcript' => $result['text'],
                'transcript_language' => $result['language'],
                'transcript_processed_at' => now(),
                'transcript_hindi' => $translationService->translate($result['text'], 'hi'),
            ]);
        } else {
            $video->update([
                'transcription_status' => 'failed',
                'transcript_error_message' => $result['error'] ?? 'Transcription failed',
            ]);
        }
    }

    private function processAI(VideoDownload $video, AIService $aiService): void
    {
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

#### 6.2 Configure Queue

**config/queue.php** - Use database driver for development:
```php
'default' => env('QUEUE_CONNECTION', 'database'),
```

**Create jobs table:**
```bash
php artisan queue:table
php artisan migrate
```

**Run queue worker:**
```bash
php artisan queue:work
```

---

### Phase 7: Frontend Migration (Inertia.js + React)

#### 7.1 Update React Components for Inertia.js

**resources/js/Pages/Videos/Index.jsx**
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
                            <img
                                src={video.cover_url}
                                alt={video.title}
                                className="w-full h-48 object-cover rounded mb-4"
                            />
                            <h3 className="font-bold text-lg mb-2">{video.title}</h3>
                            <p className="text-sm text-gray-600 mb-2">
                                Status: {video.status}
                            </p>
                            <p className="text-sm text-gray-600">
                                Transcription: {video.transcription_status}
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

**resources/js/Pages/Videos/Show.jsx**
```jsx
import { Head, Link, router } from '@inertiajs/react';
import { useState, useEffect } from 'react';
import Layout from '@/Components/Layout';

export default function Show({ video: initialVideo }) {
    const [video, setVideo] = useState(initialVideo);
    const [processing, setProcessing] = useState(false);

    // Poll for updates if processing
    useEffect(() => {
        if (
            video.transcription_status === 'transcribing' ||
            video.ai_processing_status === 'processing'
        ) {
            const interval = setInterval(() => {
                router.reload({ only: ['video'], preserveState: true });
            }, 3000);

            return () => clearInterval(interval);
        }
    }, [video.transcription_status, video.ai_processing_status]);

    const handleTranscribe = () => {
        setProcessing(true);
        router.post(`/videos/${video.id}/transcribe`, {}, {
            preserveScroll: true,
            onFinish: () => setProcessing(false),
        });
    };

    const handleProcessAI = () => {
        setProcessing(true);
        router.post(`/videos/${video.id}/process-ai`, {}, {
            preserveScroll: true,
            onFinish: () => setProcessing(false),
        });
    };

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

                        <div>
                            <h2 className="font-bold">Transcription</h2>
                            <p>Status: {video.transcription_status}</p>
                            {video.transcription_status !== 'transcribed' && (
                                <button
                                    onClick={handleTranscribe}
                                    disabled={processing}
                                    className="mt-2 bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:opacity-50"
                                >
                                    Start Transcription
                                </button>
                            )}
                            {video.transcript && (
                                <div className="mt-2 p-4 bg-gray-100 rounded">
                                    <p>{video.transcript}</p>
                                </div>
                            )}
                        </div>

                        <div>
                            <h2 className="font-bold">AI Processing</h2>
                            <p>Status: {video.ai_processing_status}</p>
                            {video.ai_processing_status !== 'processed' && (
                                <button
                                    onClick={handleProcessAI}
                                    disabled={processing}
                                    className="mt-2 bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600 disabled:opacity-50"
                                >
                                    Process with AI
                                </button>
                            )}
                            {video.ai_summary && (
                                <div className="mt-2 p-4 bg-gray-100 rounded">
                                    <p>{video.ai_summary}</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </Layout>
    );
}
```

**resources/js/Pages/Dashboard.jsx**
```jsx
import { Head } from '@inertiajs/react';
import Layout from '@/Components/Layout';

export default function Dashboard({ stats }) {
    return (
        <Layout>
            <Head title="Dashboard" />
            
            <div className="container mx-auto px-4 py-8">
                <h1 className="text-3xl font-bold mb-6">Dashboard</h1>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                    <div className="bg-white rounded-lg shadow p-6">
                        <h3 className="text-gray-600 text-sm mb-2">Total Videos</h3>
                        <p className="text-3xl font-bold">{stats.total_videos}</p>
                    </div>

                    <div className="bg-white rounded-lg shadow p-6">
                        <h3 className="text-gray-600 text-sm mb-2">Successful</h3>
                        <p className="text-3xl font-bold text-green-600">
                            {stats.successful_videos}
                        </p>
                    </div>

                    <div className="bg-white rounded-lg shadow p-6">
                        <h3 className="text-gray-600 text-sm mb-2">Transcribed</h3>
                        <p className="text-3xl font-bold text-blue-600">
                            {stats.transcribed_videos}
                        </p>
                    </div>

                    <div className="bg-white rounded-lg shadow p-6">
                        <h3 className="text-gray-600 text-sm mb-2">AI Processed</h3>
                        <p className="text-3xl font-bold text-purple-600">
                            {stats.ai_processed_videos}
                        </p>
                    </div>
                </div>

                <div className="bg-white rounded-lg shadow p-6">
                    <h2 className="text-xl font-bold mb-4">Recent Videos</h2>
                    <div className="space-y-2">
                        {stats.recent_videos.map((video) => (
                            <div key={video.id} className="border-b pb-2">
                                <p className="font-semibold">{video.title}</p>
                                <p className="text-sm text-gray-600">
                                    {video.status} • {video.transcription_status}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </Layout>
    );
}
```

#### 7.2 Create Layout Component

**resources/js/Components/Layout.jsx**
```jsx
import { Link } from '@inertiajs/react';

export default function Layout({ children }) {
    return (
        <div className="min-h-screen bg-gray-100">
            <nav className="bg-white shadow">
                <div className="container mx-auto px-4">
                    <div className="flex justify-between items-center py-4">
                        <Link href="/" className="text-xl font-bold">
                            RedNote
                        </Link>
                        <div className="space-x-4">
                            <Link href="/" className="hover:text-blue-500">
                                Dashboard
                            </Link>
                            <Link href="/videos" className="hover:text-blue-500">
                                Videos
                            </Link>
                            <Link href="/settings" className="hover:text-blue-500">
                                Settings
                            </Link>
                        </div>
                    </div>
                </div>
            </nav>

            <main>{children}</main>
        </div>
    );
}
```

---

### Phase 8: Routes Configuration

**routes/web.php**
```php
<?php

use App\Http\Controllers\DashboardController;
use App\Http\Controllers\VideoController;
use App\Http\Controllers\SettingsController;
use Illuminate\Support\Facades\Route;

Route::get('/', [DashboardController::class, 'index'])->name('dashboard');

Route::resource('videos', VideoController::class);

Route::post('/videos/extract', [VideoController::class, 'extract'])->name('videos.extract');
Route::post('/videos/{video}/transcribe', [VideoController::class, 'transcribe'])->name('videos.transcribe');
Route::post('/videos/{video}/process-ai', [VideoController::class, 'processAI'])->name('videos.process-ai');

Route::get('/settings', [SettingsController::class, 'index'])->name('settings');
Route::post('/settings', [SettingsController::class, 'update'])->name('settings.update');
```

---

### Phase 9: Configuration Files

#### 9.1 Environment Configuration

**.env**
```env
APP_NAME="RedNote"
APP_ENV=local
APP_KEY=
APP_DEBUG=true
APP_URL=http://localhost

DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=youtubefinal
DB_USERNAME=root
DB_PASSWORD=

QUEUE_CONNECTION=database

# NCA Toolkit API
NCA_API_URL=http://localhost:8080
NCA_API_KEY=your_api_key
NCA_API_ENABLED=true

# Gemini AI
GEMINI_API_KEY=your_gemini_api_key

# Cloudinary
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

# Google Sheets
GOOGLE_SHEETS_SPREADSHEET_ID=
GOOGLE_SHEETS_CREDENTIALS_JSON=
```

**config/services.php**
```php
return [
    // ... other services

    'nca' => [
        'api_url' => env('NCA_API_URL'),
        'api_key' => env('NCA_API_KEY'),
        'enabled' => env('NCA_API_ENABLED', false),
    ],

    'gemini' => [
        'api_key' => env('GEMINI_API_KEY'),
    ],

    'cloudinary' => [
        'cloud_name' => env('CLOUDINARY_CLOUD_NAME'),
        'api_key' => env('CLOUDINARY_API_KEY'),
        'api_secret' => env('CLOUDINARY_API_SECRET'),
    ],
];
```

---

## 📦 Required PHP Packages

**composer.json** dependencies:
```json
{
    "require": {
        "laravel/framework": "^11.0",
        "inertiajs/inertia-laravel": "^1.0",
        "guzzlehttp/guzzle": "^7.0",
        "cloudinary-labs/cloudinary-laravel": "^2.0",
        "google/apiclient": "^2.0"
    }
}
```

Install:
```bash
composer require inertiajs/inertia-laravel
composer require guzzlehttp/guzzle
composer require cloudinary-labs/cloudinary-laravel
composer require google/apiclient
```

---

## 🔄 Migration Checklist

### Backend
- [ ] Setup Laravel project
- [ ] Install Inertia.js
- [ ] Create database migrations
- [ ] Create models
- [ ] Create service classes
- [ ] Create controllers
- [ ] Setup background jobs/queues
- [ ] Configure file storage
- [ ] Setup external service integrations
- [ ] Create API endpoints (if needed for external access)

### Frontend
- [ ] Install React + Inertia.js
- [ ] Convert React Router pages to Inertia pages
- [ ] Replace API calls with Inertia router
- [ ] Update form submissions to use Inertia
- [ ] Migrate state management (if using Zustand/Redux)
- [ ] Update components to use Inertia props
- [ ] Test all pages and functionality

### External Services
- [ ] NCA Toolkit API integration
- [ ] Gemini AI integration
- [ ] Cloudinary integration
- [ ] Google Sheets integration
- [ ] Video extraction services (Seekin, yt-dlp)

### Testing
- [ ] Unit tests for services
- [ ] Feature tests for controllers
- [ ] Frontend component tests
- [ ] Integration tests
- [ ] End-to-end testing

---

## 🚀 Running the Application

### Development

```bash
# Terminal 1: Laravel server
php artisan serve

# Terminal 2: Vite dev server
npm run dev

# Terminal 3: Queue worker
php artisan queue:work
```

### Production

```bash
# Build assets
npm run build

# Optimize Laravel
php artisan config:cache
php artisan route:cache
php artisan view:cache

# Run queue worker (use supervisor)
php artisan queue:work --daemon
```

---

## 📚 Additional Resources

- [Laravel Documentation](https://laravel.com/docs)
- [Inertia.js Documentation](https://inertiajs.com)
- [React Documentation](https://react.dev)
- [Laravel Queues](https://laravel.com/docs/queues)
- [Laravel File Storage](https://laravel.com/docs/filesystem)

---

## 🎯 Key Differences from Django

1. **Routing**: Laravel uses `routes/web.php` instead of Django's `urls.py`
2. **Views**: Inertia.js replaces REST API - return React components directly
3. **Models**: Eloquent ORM instead of Django ORM
4. **Migrations**: Laravel migrations instead of Django migrations
5. **Background Jobs**: Laravel Queues instead of Django Celery
6. **File Storage**: Laravel Storage instead of Django FileField
7. **Validation**: Form Requests instead of Django Forms
8. **Authentication**: Laravel Breeze/Jetstream instead of Django Auth

---

## 💡 Tips for Migration

1. **Start Small**: Migrate one feature at a time
2. **Keep Django Running**: Run both systems in parallel during migration
3. **Test Thoroughly**: Test each migrated feature before moving to the next
4. **Use Queues**: Move all heavy processing to background jobs
5. **Leverage Inertia**: Use Inertia's features like partial reloads and form helpers
6. **Monitor Performance**: Use Laravel Telescope for debugging
7. **Document Changes**: Keep track of what's been migrated

---

**Good luck with your migration! 🚀**

