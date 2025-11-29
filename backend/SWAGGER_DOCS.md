# Swagger UI API Documentation

## Accessing Swagger UI

Once the FastAPI server is running, access Swagger UI at:

**http://localhost:8000/docs**

## What is Swagger UI?

Swagger UI is an interactive API documentation interface that allows you to:

1. **Browse all endpoints** - See all available API endpoints organized by tags
2. **View schemas** - See request/response models with field descriptions
3. **Test endpoints** - Execute API calls directly from the browser
4. **See examples** - View example requests and responses
5. **Understand parameters** - See required/optional parameters with descriptions

## Using Swagger UI

### 1. Viewing Endpoints

All endpoints are grouped by tags:
- **Videos** - Video extraction, transcription, processing
- **AI Settings** - AI provider configuration
- **Bulk Operations** - Batch operations on videos
- **Retry Operations** - Retry failed pipeline steps
- **XTTS** - Text-to-speech voice cloning

### 2. Testing an Endpoint

1. Click on an endpoint to expand it
2. Click "Try it out"
3. Fill in the parameters (if any)
4. Click "Execute"
5. See the response below

### 3. Example: Extract Video

1. Go to **POST /api/videos/extract/**
2. Click "Try it out"
3. In the request body, enter:
   ```json
   {
     "url": "https://www.xiaohongshu.com/explore/..."
   }
   ```
4. Click "Execute"
5. View the response with video metadata

### 4. Example: List Videos

1. Go to **GET /api/videos/**
2. Click "Try it out"
3. Optionally add query parameters:
   - `status`: Filter by status (success, failed, pending)
   - `transcription_status`: Filter by transcription status
   - `search`: Search in titles
4. Click "Execute"
5. See the list of videos

## API Endpoints Reference

### Videos

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/videos/extract/` | Extract video from URL |
| GET | `/api/videos/` | List all videos |
| GET | `/api/videos/{video_id}/` | Get video details |
| POST | `/api/videos/{video_id}/download/` | Download video locally |
| POST | `/api/videos/{video_id}/transcribe/` | Start transcription |
| GET | `/api/videos/{video_id}/transcription_status/` | Get transcription status |
| POST | `/api/videos/{video_id}/process_ai/` | Start AI processing |
| POST | `/api/videos/{video_id}/synthesize/` | Synthesize audio |
| POST | `/api/videos/{video_id}/reprocess/` | Reprocess video |
| DELETE | `/api/videos/{video_id}/delete/` | Delete video |

### AI Settings

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/ai-settings/` | Get AI provider settings |
| POST | `/api/ai-settings/` | Update AI provider settings |

### Bulk Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/bulk/delete/` | Delete multiple videos |

### Retry Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/videos/{video_id}/retry/transcription/` | Retry transcription |
| POST | `/api/videos/{video_id}/retry/ai-processing/` | Retry AI processing |
| POST | `/api/videos/{video_id}/retry/tts-synthesis/` | Retry TTS synthesis |

### XTTS

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/xtts/languages/` | Get supported languages |
| GET | `/api/xtts/voices/` | List saved voices |
| POST | `/api/xtts/voices/` | Save a new voice |
| DELETE | `/api/xtts/voices/{voice_id}/` | Delete a voice |
| POST | `/api/xtts/generate/` | Generate speech |

## Request/Response Schemas

### VideoExtractRequest
```json
{
  "url": "string"  // Required: Xiaohongshu/RedNote video URL
}
```

### VideoExtractResponse
```json
{
  "video_url": "string",
  "title": "string",
  "cover_url": "string",
  "method": "string",
  "id": 0,
  "cached": false,
  "auto_processing": false,
  "message": "string"
}
```

### VideoResponse
```json
{
  "id": 0,
  "url": "string",
  "title": "string",
  "original_title": "string",
  "description": "string",
  "cover_url": "string",
  "video_url": "string",
  "status": "string",
  "transcription_status": "string",
  "ai_processing_status": "string",
  "audio_prompt_status": "string",
  "transcript_hindi": "string",
  "is_downloaded": false,
  "extraction_method": "string",
  "created_at": "2024-01-01T00:00:00"
}
```

## Testing Workflow

### Complete Video Processing Flow

1. **Extract Video**
   - POST `/api/videos/extract/` with URL
   - Returns video metadata and starts auto-processing

2. **Check Status**
   - GET `/api/videos/{video_id}/` to see current status
   - GET `/api/videos/{video_id}/transcription_status/` for transcription

3. **Manual Processing** (if auto-processing didn't run)
   - POST `/api/videos/{video_id}/transcribe/` to start transcription
   - POST `/api/videos/{video_id}/process_ai/` to start AI processing
   - POST `/api/videos/{video_id}/synthesize/` to synthesize audio

4. **Reprocess** (if needed)
   - POST `/api/videos/{video_id}/reprocess/` to run full pipeline again

## Alternative: ReDoc

ReDoc provides an alternative documentation view at:

**http://localhost:8000/redoc**

ReDoc is more focused on reading documentation, while Swagger UI is better for testing.

## OpenAPI JSON

The raw OpenAPI schema is available at:

**http://localhost:8000/openapi.json**

This can be imported into tools like Postman, Insomnia, or other API clients.

## Tips

1. **Use "Try it out"** - This is the easiest way to test endpoints
2. **Check response schemas** - Click "Schema" to see the response structure
3. **View examples** - Many endpoints show example requests
4. **Check status codes** - See what HTTP status codes each endpoint returns
5. **Read descriptions** - Each endpoint has a detailed description

## Troubleshooting

### Swagger UI not loading?
- Make sure the server is running on the correct port
- Check browser console for errors
- Try accessing `/openapi.json` directly

### Can't execute requests?
- Check CORS settings if calling from a different origin
- Verify the server is running
- Check server logs for errors

### Authentication errors?
- Currently no authentication is required
- If you add authentication later, use the "Authorize" button in Swagger UI

