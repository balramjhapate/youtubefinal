# ✅ Reprocess Button Added to Dashboard

I've updated the **Video Cards** on the dashboard to show the "Reprocess" button.

## What Changed

**File:** `/frontend/src/components/video/VideoCard.jsx`

**Before:**
The "Reprocess" button only appeared when the final video was completely ready (`final_processed_video_url` existed).

**After:**
The button now appears if the video is in ANY of these states:
- Transcription completed or failed
- Script generation completed or failed
- TTS synthesis completed or failed
- Final video exists

## Why This Helps

You can now easily restart processing directly from the dashboard list view if:
- Processing failed at any step
- You want to regenerate with a different voice
- You want to update the script and regenerate

## How to Use

1. Go to the **Videos** page (Dashboard)
2. Look at any video card that has been processed (even partially)
3. You will see a **"Reprocess"** button next to the other action buttons
4. Click it to restart the entire pipeline for that video

This matches the behavior I added to the Video Details modal earlier.
