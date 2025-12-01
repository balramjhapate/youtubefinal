# RedNote - Video Download & Processing System

A Django-based video download and processing system for Xiaohongshu (RedNote) videos with AI transcription, captioning, and analysis capabilities.

## Features

-   🎥 **Video Download**: Download videos from Xiaohongshu URLs
-   📝 **Fast Transcription**: API-based or local Whisper transcription (10-100x faster with API)
-   🤖 **AI Processing**: Generate summaries and tags using AI
-   📊 **Smart Dashboard**: Beautiful admin interface with statistics
-   🎨 **Video Processing**: Captioning, thumbnail extraction, video trimming
-   🌍 **Multi-language**: Auto-detect and transcribe Chinese, English, and 99+ languages

## Project Structure

The project is organized into the following components:

### Active Components

-   `backend/`: **Active Django Backend** (API, Database, Video Processing)
    - This is the currently running backend with all features
    - Database: `backend/db.sqlite3`
    - Media files: `backend/media/`
-   `frontend/`: React application (User Interface)

### Other Components

-   `archived_backends/`: Archived/unused backend versions
-   `youtube_laravel/`: Separate Laravel project (PHP-based, not currently integrated)

**Note**: The backend is located in `backend/`. The `run_project.sh` script automatically uses the correct location.

## Quick Start

### 1. Run the Project (One Command)

We have provided a unified script to run both the backend and frontend simultaneously.

```bash
./run_project.sh
```

This will start:
-   **Django Backend**: http://localhost:8000/
-   **React Frontend**: http://localhost:5173/

### 2. Manual Startup (Alternative)

If you prefer to run them separately:

**Backend:**
```bash
cd backend
source venv/bin/activate
python3 manage.py runserver
```

**Frontend:**
```bash
cd frontend
npm run dev
```

## Prerequisites

-   Python 3.9 or higher
-   Node.js & npm
-   pip (Python package manager)
-   ffmpeg (for local video processing)

## Configuration

### Backend Settings
All backend settings are in `backend/settings.py`.

### Frontend Settings
Frontend configuration is in `frontend/vite.config.js`.

## Support

-   **Setup Issues**: See `NCA_TOOLKIT_SETUP.md`
-   **Integration Guide**: See `INTEGRATION_SUMMARY.md`
-   **Backend Structure**: See `BACKEND_STRUCTURE_ANALYSIS.md` for detailed explanation of project structure

---

**Happy Video Processing! 🎥✨**
