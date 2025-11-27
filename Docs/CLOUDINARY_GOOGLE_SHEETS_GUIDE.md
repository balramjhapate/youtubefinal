# Cloudinary & Google Sheets Integration Guide

## How It Works

The Cloudinary upload and Google Sheets sync happen **automatically** when a video finishes processing. Here's the complete flow:

### Automatic Process (For New Videos)

1. **Process a Video** → Click "Process Video" button on any video
2. **System Automatically:**
   - Transcribes the video
   - Generates Hindi script
   - Creates TTS audio
   - Combines audio with video (creates final processed video)
   - **Generates metadata** (title, description, tags) using AI
   - **Uploads to Cloudinary** (if enabled in settings)
   - **Adds to Google Sheets** (if enabled in settings)

### What Gets Uploaded to Cloudinary

- **Final processed video** (with Hindi TTS audio)
- Stored in folder: `videos/final/`
- URL saved in: `video.cloudinary_url`

### What Gets Added to Google Sheets

Each row contains:
- **Title** - AI-generated Hindi title
- **Description** - AI-generated Hindi description  
- **Tags** - AI-generated English tags (comma-separated)
- **Video Link (Cloudinary)** - Cloudinary URL of the video
- **Original URL** - Original video source URL
- **Video ID** - Unique video identifier
- **Duration (seconds)** - Video length
- **Created At** - When video was created
- **Status** - Review status (pending_review, approved, etc.)
- **Synced At** - When data was added to sheet

## Manual Upload/Sync for Existing Videos

If you have videos that were processed before enabling Cloudinary/Google Sheets, you can manually trigger the upload and sync.

### Option 1: Via API (Recommended)

Use the API endpoint to manually trigger upload and sync:

```bash
POST /api/videos/{video_id}/upload_and_sync/
```

This will:
1. Generate metadata (if not already generated)
2. Upload to Cloudinary (if enabled and not already uploaded)
3. Add to Google Sheets (if enabled and not already synced)

### Option 2: Reprocess Video

1. Open the video details
2. Click "Reprocess Video" button
3. This will re-run the entire pipeline including Cloudinary upload and Google Sheets sync

## Testing the Integration

### Step 1: Verify Settings

1. Go to **Settings** page
2. **Cloudinary Settings:**
   - ✅ Enable Cloudinary uploads (checkbox)
   - Enter Cloud Name
   - Enter API Key
   - Enter API Secret
   - Click "Save Cloudinary Settings"

3. **Google Sheets Settings:**
   - ✅ Enable Google Sheets tracking (checkbox)
   - Enter Spreadsheet ID or URL
   - Enter Sheet Name (default: Sheet1)
   - Paste Service Account JSON credentials
   - Click "Save Google Sheets Settings"

### Step 2: Process a Test Video

1. Go to **Videos** page
2. Extract or upload a video
3. Click on the video card to open details
4. Click **"Process Video"** button
5. Wait for processing to complete

### Step 3: Verify Results

**Check Cloudinary:**
- Go to your Cloudinary dashboard
- Navigate to Media Library → videos/final/
- You should see your uploaded video

**Check Google Sheets:**
- Open your Google Sheet
- You should see a new row with:
  - Title, Description, Tags
  - Cloudinary video link
  - Other metadata

**Check Video Details:**
- Open the video in the app
- Look for:
  - `cloudinary_url` field (should have a URL)
  - `generated_title`, `generated_description`, `generated_tags` fields
  - `google_sheets_synced` should be `true`

## Troubleshooting

### Cloudinary Upload Not Working

**Check:**
1. Settings are saved and enabled
2. Credentials are correct (cloud name, API key, API secret)
3. Check Django server logs for errors
4. Verify Cloudinary account has sufficient storage/quota

**Common Errors:**
- `Invalid credentials` → Check API key/secret
- `Upload failed` → Check file size limits in Cloudinary
- `Not configured` → Enable Cloudinary in settings

### Google Sheets Not Working

**Check:**
1. Settings are saved and enabled
2. Spreadsheet ID is correct (extracted from URL)
3. Service Account JSON is valid
4. Service Account email has edit access to the sheet
5. Google Sheets API is enabled in Google Cloud Console

**Common Errors:**
- `Permission denied` → Share sheet with service account email
- `Invalid credentials` → Check JSON credentials format
- `Sheet not found` → Verify spreadsheet ID and sheet name

### Metadata Not Generated

**Check:**
1. AI Provider is configured in Settings
2. AI API key is valid
3. Video has transcript (required for metadata generation)
4. Check Django server logs for AI API errors

## API Endpoints

### Get Video Details (Check Upload Status)

```bash
GET /api/videos/{video_id}/
```

Response includes:
- `cloudinary_url` - Cloudinary video URL (if uploaded)
- `cloudinary_uploaded_at` - Upload timestamp
- `generated_title` - AI-generated title
- `generated_description` - AI-generated description
- `generated_tags` - AI-generated tags
- `google_sheets_synced` - Whether synced to sheets
- `google_sheets_synced_at` - Sync timestamp

### Manual Upload and Sync

```bash
POST /api/videos/{video_id}/upload_and_sync/
```

This endpoint will:
1. Generate metadata if missing
2. Upload to Cloudinary if enabled and not uploaded
3. Sync to Google Sheets if enabled and not synced

## Notes

- **Cloudinary upload** only happens if:
  - Cloudinary is enabled in settings
  - Video has a final processed video file
  - Upload hasn't already been done

- **Google Sheets sync** only happens if:
  - Google Sheets is enabled in settings
  - Video has been uploaded to Cloudinary (or has final_processed_video_url)
  - Sync hasn't already been done

- **Metadata generation** requires:
  - AI Provider configured
  - Video transcript available
  - AI API key valid

