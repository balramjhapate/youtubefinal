# FastAPI Video Processing API

This is the FastAPI version of the video processing application, replacing Django for better performance and automatic API documentation.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements_fastapi.txt
```

### 2. Set Environment Variables (Optional)

Create a `.env` file in the `backend` directory:

```env
HOST=0.0.0.0
PORT=8000
DEBUG=True
DATABASE_URL=sqlite:///./db.sqlite3
NCA_API_ENABLED=False
NCA_API_URL=http://localhost:8080
NCA_API_KEY=your_api_key_here
GEMINI_API_KEY=your_gemini_key_here
```

### 3. Run the Application

```bash
python run_fastapi.py
```

Or using uvicorn directly:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Access the API

-   **Swagger UI (Interactive API Docs)**: http://localhost:8000/docs
-   **ReDoc (Alternative Docs)**: http://localhost:8000/redoc
-   **API Base URL**: http://localhost:8000/api
-   **Health Check**: http://localhost:8000/health

## 📚 API Documentation

### Swagger UI

FastAPI automatically generates interactive API documentation at `/docs`. You can:

-   **View all endpoints** with descriptions
-   **Test endpoints directly** in the browser
-   **See request/response schemas**
-   **Try different parameters**

### Available Endpoints

#### Videos

-   `POST /api/videos/extract/` - Extract video from URL
-   `GET /api/videos/` - List all videos (with filters)
-   `GET /api/videos/{video_id}/` - Get video details
-   `POST /api/videos/{video_id}/download/` - Download video locally
-   `POST /api/videos/{video_id}/transcribe/` - Start transcription
-   `GET /api/videos/{video_id}/transcription_status/` - Get transcription status
-   `POST /api/videos/{video_id}/process_ai/` - Start AI processing
-   `POST /api/videos/{video_id}/synthesize/` - Synthesize audio
-   `POST /api/videos/{video_id}/reprocess/` - Reprocess video (full pipeline)
-   `DELETE /api/videos/{video_id}/delete/` - Delete video

#### AI Settings

-   `GET /api/ai-settings/` - Get AI provider settings
-   `POST /api/ai-settings/` - Update AI provider settings

#### Bulk Operations

-   `POST /api/bulk/delete/` - Delete multiple videos

#### Retry Operations

-   `POST /api/videos/{video_id}/retry/transcription/` - Retry failed transcription
-   `POST /api/videos/{video_id}/retry/ai-processing/` - Retry failed AI processing
-   `POST /api/videos/{video_id}/retry/tts-synthesis/` - Retry failed TTS synthesis

#### XTTS (Text-to-Speech)

-   `GET /api/xtts/languages/` - Get supported languages
-   `GET /api/xtts/voices/` - List saved voices
-   `POST /api/xtts/voices/` - Save a new voice
-   `DELETE /api/xtts/voices/{voice_id}/` - Delete a voice
-   `POST /api/xtts/generate/` - Generate speech

## 🔧 Configuration

### Database

The application uses **MySQL** by default.

**Setup Steps:**

1. Create a `.env` file with MySQL credentials:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=youtubefinal
```

2. Initialize the database:

```bash
python init_database.py
```

This will create the database and all tables automatically.

See `DATABASE_SETUP.md` for detailed instructions.

### CORS

CORS is configured to allow requests from:

-   `http://localhost:3000` (React default)
-   `http://localhost:5173` (Vite default)

To add more origins, update `CORS_ORIGINS` in `app/config.py`.

## 📝 Example API Calls

### Extract Video

```bash
curl -X POST "http://localhost:8000/api/videos/extract/" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.xiaohongshu.com/explore/..."}'
```

### List Videos

```bash
curl "http://localhost:8000/api/videos/?status=success"
```

### Transcribe Video

```bash
curl -X POST "http://localhost:8000/api/videos/1/transcribe/"
```

### Get Transcription Status

```bash
curl "http://localhost:8000/api/videos/1/transcription_status/"
```

## 🆚 Differences from Django

1. **No Django Admin**: Use Swagger UI instead for testing
2. **Automatic API Docs**: Swagger UI is built-in
3. **Better Performance**: FastAPI is faster than Django for API endpoints
4. **Type Safety**: Pydantic schemas provide automatic validation
5. **Async Support**: Can handle async operations (future enhancement)

## 🔄 Migration from Django

The database schema is compatible. If you have an existing Django database:

1. The SQLite database file can be reused
2. Tables will be created automatically if they don't exist
3. Existing data will be preserved

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Change port in .env or run with different port
uvicorn app.main:app --port 8001
```

### Database Errors

```bash
# Reinitialize database
python init_database.py
```

For MySQL connection issues, check:

-   MySQL server is running
-   Credentials in `.env` are correct
-   User has CREATE DATABASE privileges

### Import Errors

Make sure you're running from the `backend` directory:

```bash
cd backend
python run_fastapi.py
```

## 📦 Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py             # Configuration settings
│   ├── database.py           # SQLAlchemy models
│   ├── schemas.py            # Pydantic schemas
│   ├── routers/              # API route handlers
│   │   ├── videos.py
│   │   ├── ai_settings.py
│   │   ├── bulk.py
│   │   ├── retry.py
│   │   └── xtts.py
│   └── services/             # Business logic
│       ├── video_service.py
│       ├── utils.py
│       └── nca_toolkit_client.py
├── media/                    # Uploaded files
│   ├── videos/
│   ├── voices/
│   └── synthesized_audio/
├── requirements_fastapi.txt
├── run_fastapi.py
└── FASTAPI_README.md
```

## 🎯 Next Steps

1. **Test the API** using Swagger UI at `/docs`
2. **Update Frontend** to point to FastAPI instead of Django
3. **Configure NCA Toolkit** if you need transcription
4. **Set up Gemini API** for AI processing and TTS

## 📞 Support

For issues or questions:

1. Check Swagger UI documentation at `/docs`
2. Review the API endpoints and schemas
3. Check server logs for error messages
