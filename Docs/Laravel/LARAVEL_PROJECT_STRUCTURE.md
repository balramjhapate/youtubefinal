# Complete Laravel Project Structure

## 📂 Full Directory Structure

```
youtubefinal-laravel/
│
├── app/                                    # Application core
│   ├── Console/
│   │   └── Commands/                      # Artisan commands
│   │
│   ├── Exceptions/
│   │   └── Handler.php                    # Exception handler
│   │
│   ├── Http/
│   │   ├── Controllers/                   # Controllers
│   │   │   ├── Controller.php
│   │   │   ├── DashboardController.php
│   │   │   ├── VideoController.php
│   │   │   ├── TranscriptionController.php
│   │   │   ├── AIController.php
│   │   │   ├── TTSController.php
│   │   │   ├── SettingsController.php
│   │   │   ├── BulkOperationController.php
│   │   │   └── XTTSController.php
│   │   │
│   │   ├── Middleware/
│   │   │   ├── HandleInertiaRequests.php
│   │   │   └── Authenticate.php
│   │   │
│   │   ├── Requests/                     # Form Request Validation
│   │   │   ├── ExtractVideoRequest.php
│   │   │   ├── TranscribeVideoRequest.php
│   │   │   ├── ProcessAIRequest.php
│   │   │   └── UpdateSettingsRequest.php
│   │   │
│   │   └── Resources/                    # API Resources (if needed)
│   │       └── VideoResource.php
│   │
│   ├── Jobs/                             # Background Jobs
│   │   ├── ProcessVideoPipeline.php
│   │   ├── ExtractVideoJob.php
│   │   ├── TranscribeVideoJob.php
│   │   ├── ProcessAIJob.php
│   │   ├── GenerateScriptJob.php
│   │   ├── SynthesizeAudioJob.php
│   │   ├── ProcessFinalVideoJob.php
│   │   ├── UploadToCloudinaryJob.php
│   │   └── SyncGoogleSheetsJob.php
│   │
│   ├── Models/                           # Eloquent Models
│   │   ├── User.php
│   │   ├── VideoDownload.php
│   │   ├── AIProviderSettings.php
│   │   ├── SavedVoice.php
│   │   ├── WatermarkSettings.php
│   │   ├── CloudinarySettings.php
│   │   └── GoogleSheetsSettings.php
│   │
│   ├── Services/                         # Business Logic Services
│   │   ├── VideoExtractionService.php
│   │   ├── TranscriptionService.php
│   │   ├── AIService.php
│   │   ├── TranslationService.php
│   │   ├── TTSService.php
│   │   ├── VideoProcessingService.php
│   │   ├── CloudinaryService.php
│   │   ├── GoogleSheetsService.php
│   │   └── NCAToolkitClient.php
│   │
│   ├── Pipelines/                        # Processing Pipelines
│   │   └── VideoProcessingPipeline.php
│   │
│   ├── Providers/
│   │   ├── AppServiceProvider.php
│   │   ├── EventServiceProvider.php
│   │   └── RouteServiceProvider.php
│   │
│   └── Helpers/                          # Helper Functions (optional)
│       └── helpers.php
│
├── bootstrap/
│   ├── app.php
│   └── cache/
│
├── config/                               # Configuration Files
│   ├── app.php
│   ├── database.php
│   ├── filesystems.php
│   ├── queue.php
│   └── services.php                      # External service configs
│
├── database/
│   ├── factories/                        # Model Factories
│   ├── migrations/                       # Database Migrations
│   │   ├── 2024_01_01_000001_create_video_downloads_table.php
│   │   ├── 2024_01_01_000002_create_ai_provider_settings_table.php
│   │   ├── 2024_01_01_000003_create_saved_voices_table.php
│   │   ├── 2024_01_01_000004_create_watermark_settings_table.php
│   │   ├── 2024_01_01_000005_create_cloudinary_settings_table.php
│   │   └── 2024_01_01_000006_create_google_sheets_settings_table.php
│   │
│   ├── seeders/                          # Database Seeders
│   │   └── DatabaseSeeder.php
│   │
│   └── .gitignore
│
├── public/                               # Public Assets
│   ├── index.php                         # Entry point
│   └── .htaccess
│
├── resources/
│   ├── css/
│   │   └── app.css                       # Main CSS file
│   │
│   ├── js/
│   │   ├── Pages/                        # Inertia Pages (React Components)
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Videos/
│   │   │   │   ├── Index.jsx
│   │   │   │   ├── Show.jsx
│   │   │   │   └── Extract.jsx
│   │   │   ├── Settings.jsx
│   │   │   ├── VoiceCloning.jsx
│   │   │   └── ScriptGenerator.jsx
│   │   │
│   │   ├── Components/                   # Reusable React Components
│   │   │   ├── Layout/
│   │   │   │   ├── Layout.jsx
│   │   │   │   ├── Navbar.jsx
│   │   │   │   └── Sidebar.jsx
│   │   │   ├── Video/
│   │   │   │   ├── VideoCard.jsx
│   │   │   │   ├── VideoPlayer.jsx
│   │   │   │   └── VideoStatus.jsx
│   │   │   ├── Forms/
│   │   │   │   ├── ExtractVideoForm.jsx
│   │   │   │   └── SettingsForm.jsx
│   │   │   └── Common/
│   │   │       ├── Button.jsx
│   │   │       ├── Modal.jsx
│   │   │       └── Loading.jsx
│   │   │
│   │   ├── utils/                        # Utility Functions
│   │   │   ├── formatDate.js
│   │   │   └── formatDuration.js
│   │   │
│   │   ├── app.jsx                       # Inertia App Entry Point
│   │   └── bootstrap.js                  # Bootstrap JS
│   │
│   └── views/
│       └── app.blade.php                 # Inertia Root Template
│
├── routes/
│   ├── web.php                           # Web Routes
│   ├── api.php                           # API Routes (if needed)
│   └── channels.php                      # Broadcast Channels
│
├── storage/
│   ├── app/
│   │   ├── public/
│   │   │   ├── videos/                   # Stored videos
│   │   │   ├── synthesized_audio/       # TTS audio files
│   │   │   └── voices/                   # Voice files
│   │   └── .gitignore
│   ├── framework/
│   └── logs/
│
├── tests/
│   ├── Feature/                          # Feature Tests
│   │   ├── VideoExtractionTest.php
│   │   ├── TranscriptionTest.php
│   │   └── AITest.php
│   │
│   └── Unit/                             # Unit Tests
│       ├── Services/
│       └── Models/
│
├── .env                                  # Environment Variables
├── .env.example
├── .gitignore
├── artisan                               # Artisan CLI
├── composer.json                         # PHP Dependencies
├── composer.lock
├── package.json                          # Node Dependencies
├── package-lock.json
├── phpunit.xml                           # PHPUnit Config
├── vite.config.js                        # Vite Config
└── README.md
```

---

## 📝 Key File Descriptions

### Controllers (`app/Http/Controllers/`)

**VideoController.php** - Main video operations
- `index()` - List all videos
- `show($id)` - Show video details
- `extract()` - Extract video from URL
- `destroy($id)` - Delete video

**DashboardController.php** - Dashboard statistics
- `index()` - Show dashboard with stats

**SettingsController.php** - Application settings
- `index()` - Show settings page
- `update()` - Update settings

### Services (`app/Services/`)

**VideoExtractionService.php**
- `extract($url)` - Extract video from Xiaohongshu URL
- `extractViaSeekin($url)` - Use Seekin API
- `extractViaYtDlp($url)` - Use yt-dlp
- `extractVideoId($url)` - Extract video ID from URL

**TranscriptionService.php**
- `transcribe($video)` - Transcribe video
- `transcribeViaNCA($video)` - Use NCA Toolkit API
- `transcribeViaWhisper($video)` - Use local Whisper

**AIService.php**
- `processVideo($video)` - Process video with AI
- `processWithGemini($video, $apiKey)` - Use Gemini AI

**TTSService.php**
- `synthesize($text, $voice)` - Generate speech
- `synthesizeWithGemini($text)` - Use Gemini TTS
- `synthesizeWithXTTS($text, $voice)` - Use XTTS

### Jobs (`app/Jobs/`)

**ProcessVideoPipeline.php** - Main pipeline job
- Handles entire video processing workflow
- Dispatches sub-jobs for each step

**TranscribeVideoJob.php** - Transcription job
**ProcessAIJob.php** - AI processing job
**SynthesizeAudioJob.php** - TTS synthesis job

### Models (`app/Models/`)

**VideoDownload.php** - Main video model
- All video-related fields and relationships
- Accessors and mutators
- Scopes for filtering

**AIProviderSettings.php** - AI configuration
**SavedVoice.php** - Saved voice profiles

### Pages (`resources/js/Pages/`)

**Dashboard.jsx** - Main dashboard
**Videos/Index.jsx** - Video list
**Videos/Show.jsx** - Video details
**Settings.jsx** - Settings page

---

## 🔄 Data Flow

### Video Extraction Flow

```
User submits URL
    ↓
VideoController::extract()
    ↓
VideoExtractionService::extract()
    ↓
Create VideoDownload model
    ↓
Dispatch ProcessVideoPipeline job
    ↓
Queue Worker processes job
    ↓
Update VideoDownload status
    ↓
Frontend polls for updates
```

### Inertia.js Flow

```
User clicks link
    ↓
Inertia router.get('/videos')
    ↓
Laravel route → Controller
    ↓
Controller returns Inertia::render('Videos/Index', data)
    ↓
Inertia sends data to React component
    ↓
React component receives props
    ↓
Component renders with data
```

---

## 📦 Package Dependencies

### PHP (composer.json)

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

### JavaScript (package.json)

```json
{
    "dependencies": {
        "@inertiajs/react": "^1.0",
        "react": "^18.0",
        "react-dom": "^18.0"
    },
    "devDependencies": {
        "@vitejs/plugin-react": "^4.0",
        "vite": "^5.0",
        "tailwindcss": "^3.0"
    }
}
```

---

## 🎯 Migration Priority

1. **Phase 1**: Setup Laravel + Inertia.js (1-2 days)
2. **Phase 2**: Database migrations (1 day)
3. **Phase 3**: Models and basic controllers (2-3 days)
4. **Phase 4**: Service layer (3-4 days)
5. **Phase 5**: Background jobs (2-3 days)
6. **Phase 6**: Frontend pages (3-4 days)
7. **Phase 7**: External integrations (2-3 days)
8. **Phase 8**: Testing and optimization (2-3 days)

**Total Estimated Time: 16-22 days**

---

## 💡 Best Practices

1. **Keep Services Thin**: Business logic in services, not controllers
2. **Use Jobs for Heavy Tasks**: All video processing in background jobs
3. **Validate Early**: Use Form Requests for validation
4. **Type Safety**: Use PHP type hints and return types
5. **Error Handling**: Proper exception handling in services
6. **Logging**: Use Laravel's logging for debugging
7. **Testing**: Write tests for critical paths
8. **Documentation**: Comment complex logic

---

This structure provides a solid foundation for your Laravel + Inertia.js + React application!

