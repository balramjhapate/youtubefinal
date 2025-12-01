# Complete Video Processing Pipeline Analysis

## Pipeline Overview

The video processing pipeline runs automatically when you call the `transcribe` action endpoint. Here's the complete flow:

## Entry Point

**File:** `legacy/root_debris/downloader/api_views.py`  
**Function:** `VideoDownloadViewSet.transcribe()`  
**Line:** 562  
**Endpoint:** `POST /api/videos/{id}/transcribe/`

---

## Complete Pipeline Flow

### **Step 1: Transcription** (Lines 589-776)
**Location:** `legacy/root_debris/downloader/api_views.py:589`

1. **Status Update:** Sets `transcription_status = 'transcribing'`
2. **Transcription Process:**
   - Calls `transcribe_video(video)` from `utils.py`
   - Uses NCA Toolkit or Whisper for transcription
   - Generates transcript with timestamps
   - Generates transcript without timestamps
   - Translates to Hindi if needed
3. **Save Results:**
   - `video.transcript` - Full transcript with timestamps
   - `video.transcript_without_timestamps` - Plain text
   - `video.transcript_hindi` - Hindi translation
   - `video.transcript_language` - Detected language
   - Sets `transcription_status = 'transcribed'`

---

### **Step 2: AI Processing** (Lines 777-835)
**Location:** `legacy/root_debris/downloader/api_views.py:777`

1. **AI Enhancement:**
   - Enhances transcript using AI (if not already done)
   - Sets `ai_processing_status = 'processed'`
2. **Generate Summary & Tags:**
   - Calls `process_video_with_ai(video)` from `utils.py`
   - Generates AI summary
   - Generates AI tags
3. **Save Results:**
   - `video.ai_summary` - AI-generated summary
   - `video.ai_tags` - AI-generated tags
   - `video.ai_processed_at` - Timestamp

---

### **Step 3: Script Generation** (Lines 836-926)
**Location:** `legacy/root_debris/downloader/api_views.py:836`

1. **Check Prerequisites:**
   - Requires `enhanced_transcript` or `transcript`
2. **Generate Hindi Script:**
   - Calls `generate_hindi_script(video)` from `utils.py`
   - Creates explainer-style Hindi script
3. **Save Results:**
   - `video.hindi_script` - Generated Hindi script
   - `video.script_status = 'generated'`
   - `video.script_generated_at` - Timestamp

---

### **Step 4: TTS (Text-to-Speech) Generation** (Lines 927-1049)
**Location:** `legacy/root_debris/downloader/api_views.py:927`

1. **Check Prerequisites:**
   - Requires `script_status == 'generated'` and `hindi_script`
2. **TTS Synthesis:**
   - Uses `GeminiTTSService` from `gemini_tts_service.py`
   - Cleans script using `get_clean_script_for_tts()`
   - Generates audio with voice: `Enceladus`, language: `hi-IN`
   - Adjusts audio duration to match video duration
3. **Save Results:**
   - `video.synthesized_audio` - Generated MP3 audio file
   - `video.synthesis_status = 'synthesized'`
   - `video.synthesized_at` - Timestamp

---

### **Step 5: Video Processing** (Lines 1051-1250)
**Location:** `legacy/root_debris/downloader/api_views.py:1051`

#### **Step 5a: Remove Original Audio** (Lines 1082-1110)
1. **Remove Audio:**
   - Uses `ffmpeg` to remove original audio from video
   - Command: `ffmpeg -i video.mp4 -c:v copy -an output.mp4`
2. **Save Results:**
   - `video.voice_removed_video` - Video without audio
   - `video.voice_removed_video_url` - URL to voice-removed video

#### **Step 5b: Combine TTS Audio with Video** (Lines 1115-1188)
1. **Combine Audio & Video:**
   - Uses `ffmpeg` to combine voice-removed video with TTS audio
   - Command: `ffmpeg -i video.mp4 -i audio.mp3 -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 output.mp4`
2. **Save Results:**
   - `video.final_processed_video` - Final video with new audio
   - `video.final_processed_video_url` - URL to final video
   - `video.review_status = 'pending_review'`

#### **Step 5c: Apply Watermark** (Lines 1141-1177)
1. **Check Watermark Settings:**
   - Checks if watermark is enabled in `WatermarkSettings`
2. **Apply Watermark:**
   - Calls `apply_moving_watermark()` from `watermark_service.py`
   - Applies moving text watermark to final video
3. **Save Results:**
   - Updates `video.final_processed_video` with watermarked version

---

### **Step 6: Post-Processing** (Lines 1193-1236)
**Location:** `legacy/root_debris/downloader/api_views.py:1193`

This is where **Google Sheets upload happens**!

#### **6a: Generate Metadata** (Lines 1195-1203)
1. **Generate SEO Metadata:**
   - Calls `generate_video_metadata(video)` from `utils.py`
   - Generates title, description, and tags using AI
2. **Save Results:**
   - `video.generated_title` - SEO-optimized title
   - `video.generated_description` - SEO-optimized description
   - `video.generated_tags` - SEO-optimized tags

#### **6b: Upload to Cloudinary** (Lines 1205-1218)
1. **Check Cloudinary Settings:**
   - Checks if Cloudinary is enabled
2. **Upload Video:**
   - Calls `upload_video_file()` from `cloudinary_service.py`
   - Uploads `final_processed_video` to Cloudinary
   - Uses `video_id` as public_id (replaces existing if same ID)
3. **Save Results:**
   - `video.cloudinary_url` - Cloudinary video URL
   - `video.cloudinary_uploaded_at` - Timestamp

#### **6c: Upload to Google Sheets** (Lines 1223-1232) ⭐ **YOUR FUNCTION HERE**
**Location:** `legacy/root_debris/downloader/api_views.py:1223`

1. **Check Google Sheets Settings:**
   - Checks if `add_video_to_sheet` function is available
   - Checks if Google Sheets is enabled in settings
2. **Call Google Sheets Upload:**
   ```python
   if add_video_to_sheet:
       sheet_result = add_video_to_sheet(video, video.cloudinary_url)
   ```
   **Function Location:** `legacy/root_debris/downloader/google_sheets_service.py:840`
   
3. **What Happens in `add_video_to_sheet()`:**
   - Generates unique UUID for the row
   - **Generates YouTube SEO title** using Gemini API
   - **Generates YouTube SEO description** (with trending tags) using Gemini API
   - **Generates YouTube tags** using Gemini API
   - **Generates Facebook title** using Gemini API
   - **Generates Facebook description** using Gemini API
   - **Generates Facebook tags** using Gemini API
   - **Generates Instagram title** using Gemini API
   - **Generates Instagram description** using Gemini API
   - **Generates Instagram tags** using Gemini API
   - Checks for existing video by Video ID
   - Updates existing row or creates new row in Google Sheets
   - Saves sync status: `video.google_sheets_synced = True`

4. **Save Results:**
   - `video.google_sheets_synced = True`
   - `video.google_sheets_synced_at` - Timestamp

---

## Alternative Entry Points

### **Manual Upload & Sync**
**File:** `legacy/root_debris/downloader/api_views.py`  
**Function:** `VideoDownloadViewSet.upload_and_sync()`  
**Line:** 1706  
**Endpoint:** `POST /api/videos/{id}/upload_and_sync/`

This endpoint:
1. Generates metadata (if not already generated)
2. Uploads to Cloudinary
3. **Calls `add_video_to_sheet()` at line 1765**

### **Reprocess Video**
**File:** `legacy/root_debris/downloader/api_views.py`  
**Function:** `VideoDownloadViewSet.reprocess()`  
**Line:** 1806  
**Endpoint:** `POST /api/videos/{id}/reprocess/`

This endpoint:
1. Resets all processing states
2. Re-runs the complete pipeline
3. **Calls `add_video_to_sheet()` at line 2494** (in reprocess flow)

---

## Import Statement

**File:** `legacy/root_debris/downloader/api_views.py`  
**Lines:** 36-40

```python
try:
    from .google_sheets_service import add_video_to_sheet
except ImportError:
    add_video_to_sheet = None
    logger.warning("Google Sheets service not available")
```

---

## Summary

The Google Sheets upload function (`add_video_to_sheet`) is called in **3 places**:

1. **Main Pipeline** (Line 1225): After final video is created and Cloudinary upload completes
2. **Manual Upload & Sync** (Line 1765): When manually triggering upload/sync
3. **Reprocess Flow** (Line 2494): When reprocessing a video

The function is imported at the top of `api_views.py` and is called as part of the post-processing step after:
- ✅ Video transcription
- ✅ AI processing
- ✅ Script generation
- ✅ TTS synthesis
- ✅ Final video creation
- ✅ Cloudinary upload

