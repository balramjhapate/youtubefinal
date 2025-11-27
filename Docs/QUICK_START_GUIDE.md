# Quick Start Guide - Video Processing System

## Prerequisites

Before processing videos, you MUST have at least one voice sample uploaded:

1. Go to **Voice Cloning** section in the app
2. Upload a Hindi voice sample (WAV or MP3 file, 5-30 seconds recommended)
3. Name it "**default**" (this will be used automatically for all videos)
4. Or assign a specific voice profile to each video

## How to Process a Video

### Step 1: Extract/Upload Video

**Option A: Extract from URL**
1. Go to Videos page
2. Click "Extract Video" button
3. Paste video URL (YouTube, RedNote, Facebook, Instagram, Vimeo)
4. Click "Extract"

**Option B: Upload Local Video**
1. Go to Videos page
2. Click "Upload Local Video" button
3. Select video file from your computer
4. Click "Upload"

### Step 2: Process Video

1. Click on the video card to open Video Details modal
2. Click "**Process Video**" button
3. Wait for processing to complete (this happens automatically in the background)

The system will automatically:
- ✅ Transcribe the video audio
- ✅ Translate to Hindi
- ✅ Generate AI summary and tags
- ✅ Create Hindi script
- ✅ Generate TTS audio (using default voice or assigned voice)
- ✅ Adjust audio speed to match video duration
- ✅ Remove original audio from video
- ✅ Combine new Hindi audio with video

### Step 3: Download Results

Once processing is complete, you'll see 4 download links:

1. **Downloaded Video (Original with Audio)** - Original video
2. **Voice Removed Video (No Audio)** - Video without any audio
3. **🎵 Synthesized TTS Audio (Hindi)** - Generated Hindi audio file
4. **Final Processed Video (with New Hindi Audio)** - Final result!

## Troubleshooting

### "No voice profile available for TTS"

**Solution:** Upload a voice sample in Voice Cloning section and name it "default"

### Processing stuck or failed

**Solution:** 
1. Check browser console for errors (F12 → Console tab)
2. Check Django server logs for detailed error messages
3. Try clicking "Reprocess Video" button

### Audio not synced with video

**Solution:** The system automatically adjusts audio speed to match video duration. If still not synced:
1. Check video duration is correctly detected
2. Try reprocessing the video

### TTS audio sounds wrong

**Solution:**
1. Upload a better quality voice sample (clear, no background noise)
2. Use a longer voice sample (10-30 seconds recommended)
3. Try different TTS parameters in the settings

## Advanced: Manual Voice Assignment

If you want to use a specific voice for a video:

1. Upload multiple voice samples in Voice Cloning section
2. In Django Admin panel, edit the video
3. Select the desired voice profile from dropdown
4. Save and reprocess the video

## System Architecture

```
Video Input
    ↓
Download/Upload → local_file (original video)
    ↓
Transcribe → transcript (text with timestamps)
    ↓
Translate → transcript_hindi (Hindi translation)
    ↓
AI Process → ai_summary, ai_tags
    ↓
Generate Script → hindi_script (formatted for TTS)
    ↓
TTS Synthesis → synthesized_audio (Hindi audio)
    ↓
Audio Speed Adjustment → Match video duration
    ↓
Remove Audio → voice_removed_video (silent video)
    ↓
Combine → final_processed_video (video + Hindi audio)
```

## Performance Tips

- **Video Length:** Shorter videos (1-5 minutes) process faster
- **Voice Quality:** Use high-quality voice samples for better TTS results
- **Batch Processing:** Process multiple videos by clicking "Process Video" on each
- **Server Resources:** Processing uses CPU/GPU, ensure adequate resources

## API Endpoints (for developers)

- `POST /api/videos/{id}/transcribe/` - Start full processing pipeline
- `POST /api/videos/{id}/reprocess/` - Reprocess existing video
- `GET /api/videos/{id}/` - Get video details and status
- `POST /api/xtts/synthesize/` - Manual TTS synthesis
- `GET /api/cloned-voices/` - List available voices

## Files Generated

All files are stored in Django media directory:

- `videos/` - Original downloaded videos
- `videos/voice_removed/` - Videos without audio
- `videos/final/` - Final processed videos
- `synthesized_audio/` - TTS audio files
- `cloned_voices/` - Voice samples

## Next Steps

1. ✅ Upload a default voice sample
2. ✅ Extract or upload a test video
3. ✅ Click "Process Video" and wait
4. ✅ Download the final result!

For issues or questions, check the logs or contact support.
