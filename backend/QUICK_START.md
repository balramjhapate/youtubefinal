# Quick Start Guide - FastAPI Video Processing API

## 🚀 Get Started in 4 Steps

### Step 1: Install Dependencies

```bash
cd backend
pip install -r requirements_fastapi.txt
```

### Step 2: Set Up MySQL Database

1. Create a `.env` file:
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=youtubefinal
```

2. Initialize the database:
```bash
python init_database.py
```

This creates the `youtubefinal` database and all tables.

### Step 3: Run the Server

```bash
python run_fastapi.py
```

### Step 4: Open Swagger UI

Open your browser and go to:

**http://localhost:8000/docs**

That's it! You can now test all API endpoints directly in Swagger UI.

## 📝 First API Call

### Extract a Video

1. Go to **POST /api/videos/extract/**
2. Click "Try it out"
3. Enter a video URL:
   ```json
   {
     "url": "https://www.xiaohongshu.com/explore/..."
   }
   ```
4. Click "Execute"
5. See the response with video metadata

## 🔧 Configuration

Create a `.env` file with all settings:

```env
# Database - MySQL (Required)
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=youtubefinal

# NCA Toolkit API (Optional)
NCA_API_ENABLED=False
NCA_API_URL=http://localhost:8080
NCA_API_KEY=your_key_here

# Gemini API (Optional)
GEMINI_API_KEY=your_key_here
```

## 📚 Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Full README**: See `FASTAPI_README.md`
- **Swagger Guide**: See `SWAGGER_DOCS.md`

## 🎯 Common Tasks

### List All Videos
```
GET /api/videos/
```

### Get Video Details
```
GET /api/videos/1/
```

### Transcribe a Video
```
POST /api/videos/1/transcribe/
```

### Check Transcription Status
```
GET /api/videos/1/transcription_status/
```

### Process with AI
```
POST /api/videos/1/process_ai/
```

## ⚡ Key Features

- ✅ **Automatic API Documentation** - Swagger UI built-in
- ✅ **Interactive Testing** - Test endpoints directly in browser
- ✅ **Type Safety** - Pydantic schemas for validation
- ✅ **Fast Performance** - FastAPI is faster than Django
- ✅ **No Django Required** - Pure FastAPI application

## 🆘 Troubleshooting

### Port Already in Use
```bash
# Use a different port
uvicorn app.main:app --port 8001
```

### Import Errors
Make sure you're in the `backend` directory:
```bash
cd backend
python run_fastapi.py
```

### Database Issues
The database is created automatically. If you have issues:
```bash
python -c "from app.database import init_db; init_db()"
```

## 🔗 Next Steps

1. **Test the API** using Swagger UI
2. **Update Frontend** to use FastAPI endpoints
3. **Configure Services** (NCA Toolkit, Gemini) if needed
4. **Deploy** when ready

Enjoy your new FastAPI application! 🎉

