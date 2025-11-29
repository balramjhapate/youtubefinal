# Project Structure (MVC-based Organization)

This document describes the well-organized MVC-based structure of the FastAPI backend.

## Directory Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── config.py              # Application configuration
│   ├── main.py                 # FastAPI application entry point
│   ├── database.py             # Compatibility shim (deprecated - use models)
│   │
│   ├── models/                 # Database Models (MVC - Model)
│   │   ├── __init__.py         # Exports all models
│   │   ├── base.py             # Database base configuration
│   │   ├── video_download.py   # VideoDownload model
│   │   ├── ai_settings.py      # AIProviderSettings model
│   │   └── saved_voice.py      # SavedVoice model
│   │
│   ├── schemas/                # Pydantic Schemas (Request/Response Models)
│   │   ├── __init__.py         # Exports all schemas
│   │   ├── video.py            # Video-related schemas
│   │   ├── ai.py               # AI-related schemas
│   │   ├── xtts.py             # XTTS-related schemas
│   │   └── common.py           # Common schemas (bulk, retry, etc.)
│   │
│   ├── routers/                # API Routes (MVC - View/Controller)
│   │   ├── __init__.py
│   │   ├── videos.py           # Video endpoints
│   │   ├── ai_settings.py     # AI settings endpoints
│   │   ├── xtts.py             # XTTS endpoints
│   │   ├── bulk.py             # Bulk operations
│   │   └── retry.py            # Retry operations
│   │
│   └── services/               # Business Logic (MVC - Controller)
│       ├── __init__.py
│       ├── video_service.py    # Video processing logic
│       ├── utils.py            # Utility functions
│       └── nca_toolkit_client.py # NCA Toolkit client
│
├── media/                      # Media files storage
│   ├── videos/
│   ├── voices/
│   └── synthesized_audio/
│
├── init_database.py            # Database initialization script
├── check_stuck_transcriptions.py # Utility script
├── migrate_from_sqlite.py      # Migration script
└── run_fastapi.py              # Application runner
```

## MVC Architecture

### Model Layer (`app/models/`)
- **Purpose**: Database models using SQLAlchemy ORM
- **Files**:
  - `base.py`: Database engine, session factory, Base class
  - `video_download.py`: VideoDownload model
  - `ai_settings.py`: AIProviderSettings model
  - `saved_voice.py`: SavedVoice model

### View/Controller Layer (`app/routers/`)
- **Purpose**: API endpoints (FastAPI routes)
- **Files**:
  - `videos.py`: Video CRUD and processing endpoints
  - `ai_settings.py`: AI settings management
  - `xtts.py`: Text-to-speech endpoints
  - `bulk.py`: Bulk operations
  - `retry.py`: Retry failed operations

### Controller/Service Layer (`app/services/`)
- **Purpose**: Business logic and complex operations
- **Files**:
  - `video_service.py`: Video processing pipeline logic
  - `utils.py`: Helper functions
  - `nca_toolkit_client.py`: External API client

### Schema Layer (`app/schemas/`)
- **Purpose**: Pydantic models for request/response validation
- **Files**:
  - `video.py`: Video-related request/response schemas
  - `ai.py`: AI-related schemas
  - `xtts.py`: XTTS-related schemas
  - `common.py`: Shared schemas

## Import Patterns

### Models
```python
from app.models import VideoDownload, AIProviderSettings, SavedVoice
from app.models import get_db, init_db, SessionLocal
```

### Schemas
```python
from app.schemas import VideoResponse, VideoExtractRequest, VideoStatsResponse
from app.schemas import AISettingsResponse, XTTSVoiceResponse
```

### Services
```python
from app.services.video_service import VideoService
from app.services.utils import perform_extraction
```

## Benefits of This Structure

1. **Separation of Concerns**: Models, schemas, routes, and services are clearly separated
2. **Maintainability**: Easy to find and modify specific components
3. **Scalability**: Easy to add new models, routes, or services
4. **Testability**: Each layer can be tested independently
5. **Readability**: Clear organization makes code easier to understand

## Migration Notes

- Old `app.database` imports still work (via compatibility shim) but show deprecation warning
- Old `app.schemas` imports are redirected to `app.schemas` package
- All new code should use `app.models` instead of `app.database`

