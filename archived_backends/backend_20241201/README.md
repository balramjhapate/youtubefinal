# RedNote - Video Download & Processing System

A Django-based video download and processing system for Xiaohongshu (RedNote) videos with AI transcription, captioning, and analysis capabilities.

## Features

-   🎥 **Video Download**: Download videos from Xiaohongshu URLs
-   📝 **Fast Transcription**: API-based or local Whisper transcription (10-100x faster with API)
-   🤖 **AI Processing**: Generate summaries and tags using AI
-   📊 **Smart Dashboard**: Beautiful admin interface with statistics
-   🎨 **Video Processing**: Captioning, thumbnail extraction, video trimming
-   🌍 **Multi-language**: Auto-detect and transcribe Chinese, English, and 99+ languages

## Prerequisites

-   Python 3.9 or higher
-   pip (Python package manager)
-   ffmpeg (for local video processing - optional if using NCA API)
-   SQLite (included with Python)

## Quick Start

### 1. Clone/Download the Project

```bash
cd /Volumes/Data/Python/Rednote
```

### 2. Install Python Dependencies

```bash
pip3 install -r requirements.txt
```

**Note**: This will install:

-   Django 4.2
-   django-jazzmin (admin theme)
-   deep-translator (translation)
-   requests (HTTP requests)
-   openai-whisper (local transcription - optional)
-   ffmpeg-python (video processing - optional)

### 3. Install System Dependencies (Optional - only if using local processing)

**macOS:**

```bash
brew install ffmpeg
```

**Ubuntu/Debian:**

```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html

**Note**: If you're using NCA Toolkit API for processing, you don't need ffmpeg or Whisper locally.

### 4. Run Migrations

```bash
python3 manage.py migrate
```

This will create the database tables.

### 5. Create Superuser (Admin Access)

```bash
python3 manage.py createsuperuser
```

Follow the prompts to create an admin user.

### 6. Start the Development Server

```bash
python3 manage.py runserver
```

The server will start at: **http://127.0.0.1:8000/**

### 7. Access the Admin Panel

Open your browser and go to:

-   **Admin Panel**: http://127.0.0.1:8000/admin/
-   Login with the superuser credentials you created

## Using the Application

### Adding Videos

1. Go to Admin Panel → **Video Downloads**
2. Click **"Add Video Download"**
3. Paste a Xiaohongshu video URL
4. Click **Save**
5. The system will automatically:
    - Extract video metadata
    - Download the video
    - Translate titles and descriptions

### Transcribing Videos

**Option 1: Fast API Transcription (Recommended)**

1. Configure NCA Toolkit API (see `NCA_TOOLKIT_SETUP.md`)
2. Select video(s) → Actions → **"Transcribe Selected Videos"**
3. Or click **"📝 Transcribe"** button for individual videos
4. Results in **10-30 seconds** (vs 2-5 minutes locally)

**Option 2: Local Transcription**

1. Ensure Whisper and ffmpeg are installed
2. Select video(s) → Actions → **"Transcribe Selected Videos"**
3. First run will download Whisper model (~150MB)
4. Takes **2-5 minutes** per video

### Processing with AI

1. Select video(s) → Actions → **"Process Selected Videos with AI"**
2. Or click **"🤖 Process AI"** button for individual videos
3. System will:
    - Use existing transcript (if available)
    - Generate AI summary
    - Extract tags and keywords
    - Save results

### Adding Captions

1. **First transcribe** the video
2. Select video(s) → Actions → **"Add Captions to Videos (NCA API)"**
3. Requires NCA Toolkit API to be enabled

## Configuration

### Basic Settings

The project uses SQLite database by default. All settings are in `rednote_project/settings.py`.

### Enable Fast Processing (NCA Toolkit API)

For **10-100x faster** transcription and video processing:

1. **Option A: Environment Variables**

```bash
export NCA_API_URL="http://localhost:8080"
export NCA_API_KEY="your_api_key"
export NCA_API_ENABLED="true"
```

2. **Option B: Edit settings.py**

```python
NCA_API_URL = 'http://localhost:8080'  # Your NCA Toolkit API URL
NCA_API_KEY = 'your_api_key_here'      # Your API key
NCA_API_ENABLED = True                  # Enable API
NCA_API_TIMEOUT = 600                   # 10 minutes timeout
```

**To deploy NCA Toolkit API**, see: `NCA_TOOLKIT_SETUP.md`

### Media Files

Videos are stored in:

-   **Local Storage**: `media/videos/`
-   Configure `MEDIA_ROOT` in `settings.py` if needed

## Project Structure

```
Rednote/
├── downloader/          # Main app
│   ├── models.py       # VideoDownload model
│   ├── admin.py        # Admin interface
│   ├── utils.py        # Video processing functions
│   ├── nca_toolkit_client.py  # NCA API client
│   └── views.py        # API views
├── rednote_project/    # Project settings
│   └── settings.py     # Django settings
├── media/              # Uploaded videos
│   └── videos/
├── db.sqlite3          # Database
├── manage.py           # Django management script
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## Common Commands

### Run Server

```bash
python3 manage.py runserver
```

### Run Server on Different Port

```bash
python3 manage.py runserver 8001
```

### Run Migrations

```bash
python3 manage.py migrate
```

### Create Superuser

```bash
python3 manage.py createsuperuser
```

### Collect Static Files (for production)

```bash
python3 manage.py collectstatic
```

### Check for Errors

```bash
python3 manage.py check
```

### Access Django Shell

```bash
python3 manage.py shell
```

## Troubleshooting

### Server Won't Start

**Port already in use:**

```bash
# Find process using port 8000
lsof -ti:8000

# Kill the process
kill -9 $(lsof -ti:8000)

# Or use a different port
python3 manage.py runserver 8001
```

### Import Errors

```bash
# Reinstall dependencies
pip3 install -r requirements.txt
```

### Database Errors

```bash
# Delete database and recreate
rm db.sqlite3
python3 manage.py migrate
```

### Transcription Not Working

**If using local Whisper:**

1. Check if ffmpeg is installed: `ffmpeg -version`
2. Check if Whisper is installed: `pip3 show openai-whisper`
3. First transcription downloads model (~150MB)

**If using NCA API:**

1. Check if API is running: `curl http://localhost:8080/v1/toolkit/health`
2. Verify API key is correct
3. Check `NCA_API_ENABLED = True` in settings

### Permission Errors

```bash
# Make sure you have write permissions
chmod -R 755 media/
```

## Production Deployment

For production deployment:

1. **Set `DEBUG = False`** in `settings.py`
2. **Set proper `ALLOWED_HOSTS`**
3. **Use a production database** (PostgreSQL recommended)
4. **Use a production web server** (Gunicorn + Nginx)
5. **Set up static file serving**
6. **Use environment variables** for secrets

Example with Gunicorn:

```bash
pip install gunicorn
gunicorn rednote_project.wsgi:application --bind 0.0.0.0:8000
```

## Performance Tips

1. **Use NCA Toolkit API**: 10-100x faster than local processing
2. **Enable caching**: Use Redis or Memcached for better performance
3. **Use production database**: PostgreSQL is faster than SQLite
4. **Optimize media storage**: Use cloud storage (S3, GCS) for large files
5. **Background tasks**: Use Celery for long-running operations

## Support

-   **Setup Issues**: See `NCA_TOOLKIT_SETUP.md`
-   **Integration Guide**: See `INTEGRATION_SUMMARY.md`
-   **NCA Toolkit Docs**: https://github.com/stephengpope/no-code-architects-toolkit

## License

This project uses Django and other open-source libraries. See individual package licenses.

---

**Happy Video Processing! 🎥✨**
