# Backend Reorganization Plan

## Current Structure Analysis

### 1. Service Files (to move to `services/`)
- `cloudinary_service.py` - Cloudinary upload service
- `gemini_tts_service.py` - Gemini TTS service
- `google_sheets_service.py` - Google Sheets integration
- `google_tts_service.py` - Google TTS service
- `watermark_service.py` - Watermark processing
- `xtts_service.py` - XTTS voice cloning service
- `nca_toolkit_client.py` - NCA transcription client
- `visual_analysis.py` - Visual analysis service
- `whisper_transcribe.py` - Whisper transcription service
- `dual_transcribe.py` - Dual transcription service

### 2. Models (to split into `models/` folder)
Current: Single `models.py` with 6 models
- `AIProviderSettings` → `models/ai_provider_settings.py`
- `CloudinarySettings` → `models/cloudinary_settings.py`
- `GoogleSheetsSettings` → `models/google_sheets_settings.py`
- `WatermarkSettings` → `models/watermark_settings.py`
- `ClonedVoice` → `models/cloned_voice.py`
- `VideoDownload` → `models/video_download.py`
- `models/__init__.py` - Export all models

### 3. Controllers/Views (to move to `controllers/`)
- `api_views.py` - API endpoints
- `views.py` - Main views
- `script_views.py` - Script-related views
- `xtts_views.py` - XTTS views

### 4. Pipeline (to create `pipeline/` folder)
- `utils.py` - Video processing utilities (pipeline functions)
- Pipeline orchestration logic from `api_views.py`
- Processing step handlers

### 5. Other Files Organization
- `serializers.py` → `serializers/` folder (if multiple) or keep at root
- `admin.py` - Keep at root (Django convention)
- `word_filter.py` → `utils/` or `services/`
- `test_google_sheets.py` → `tests/`
- `tests.py` → `tests/`

## Proposed New Structure

```
backend/
├── models/
│   ├── __init__.py (exports all models)
│   ├── ai_provider_settings.py
│   ├── cloudinary_settings.py
│   ├── google_sheets_settings.py
│   ├── watermark_settings.py
│   ├── cloned_voice.py
│   └── video_download.py
├── services/
│   ├── __init__.py
│   ├── cloudinary_service.py
│   ├── gemini_tts_service.py
│   ├── google_sheets_service.py
│   ├── google_tts_service.py
│   ├── watermark_service.py
│   ├── xtts_service.py
│   ├── nca_toolkit_client.py
│   ├── visual_analysis.py
│   ├── whisper_transcribe.py
│   └── dual_transcribe.py
├── controllers/
│   ├── __init__.py
│   ├── api_views.py
│   ├── views.py
│   ├── script_views.py
│   └── xtts_views.py
├── pipeline/
│   ├── __init__.py
│   ├── utils.py (video processing utilities)
│   ├── orchestrator.py (main pipeline orchestration)
│   └── processors.py (step processors)
├── serializers/
│   ├── __init__.py
│   └── serializers.py (or split if needed)
├── utils/
│   ├── __init__.py
│   └── word_filter.py
├── tests/
│   ├── __init__.py
│   ├── tests.py
│   └── test_google_sheets.py
├── management/
├── templatetags/
├── migrations/
├── static/
├── templates/
├── media/
├── admin.py
├── urls.py
├── app_urls.py
├── api_urls.py
├── settings.py
├── manage.py
├── wsgi.py
├── asgi.py
└── requirements.txt
```

## Implementation Steps

1. ✅ Create folder structure
2. ✅ Move service files to `services/`
3. ✅ Split models.py into separate files in `models/`
4. ✅ Move controllers to `controllers/`
5. ✅ Create pipeline folder and organize pipeline code
6. ✅ Organize other files (serializers, utils, tests)
7. ✅ Update all imports across codebase
8. ✅ Test that everything still works

## Import Updates Required

- All files importing from `models` → `from models.xxx import`
- All files importing services → `from services.xxx import`
- All files importing views → `from controllers.xxx import`
- Pipeline imports → `from pipeline.xxx import`

