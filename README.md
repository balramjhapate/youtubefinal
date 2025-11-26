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

The project is organized into two main components:

-   `backend/`: Django application (API, Database, Video Processing)
-   `frontend/`: React application (User Interface)

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
All backend settings are in `backend/rednote_project/settings.py`.

### Frontend Settings
Frontend configuration is in `frontend/vite.config.js`.

## Support

-   **Setup Issues**: See `NCA_TOOLKIT_SETUP.md`
-   **Integration Guide**: See `INTEGRATION_SUMMARY.md`

---

**Happy Video Processing! 🎥✨**
