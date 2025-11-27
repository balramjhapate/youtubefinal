# Video Processing Pipeline - Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         VIDEO INPUT                                  │
│  (URL Extract OR Local Upload)                                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 1: DOWNLOAD/SAVE VIDEO                                        │
│  ✓ Save to: local_file                                              │
│  ✓ Extract duration using ffprobe                                   │
│  ✓ Calculate TTS parameters (speed, temperature)                    │
│  Status: is_downloaded = True                                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 2: TRANSCRIBE AUDIO                                           │
│  ✓ Extract audio from video                                         │
│  ✓ Use Whisper to transcribe                                        │
│  ✓ Save transcript WITH timestamps → transcript                     │
│  ✓ Save transcript WITHOUT timestamps → transcript_without_timestamps│
│  ✓ Detect language → transcript_language                            │
│  Status: transcription_status = 'transcribed'                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 3: TRANSLATE TO HINDI                                         │
│  ✓ Translate transcript to Hindi                                    │
│  ✓ Save Hindi translation → transcript_hindi                        │
│  Status: transcript_hindi populated                                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 4: AI PROCESSING                                              │
│  ✓ Generate summary using AI (Gemini/OpenAI/Anthropic)             │
│  ✓ Generate tags → ai_tags                                          │
│  ✓ Save summary → ai_summary                                        │
│  Status: ai_processing_status = 'processed'                          │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 5: GENERATE HINDI SCRIPT                                      │
│  ✓ Use AI to create natural Hindi script                            │
│  ✓ Optimize for TTS (remove timestamps, clean text)                 │
│  ✓ Save script → hindi_script                                       │
│  ✓ Save clean version → clean_script_for_tts (via serializer)      │
│  Status: script_status = 'generated'                                 │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 6: TTS SYNTHESIS (XTTS v2)                                    │
│  ✓ Get voice profile:                                               │
│    1. Check if video.voice_profile assigned                         │
│    2. Fallback to ClonedVoice named "default"                       │
│    3. Fallback to first available ClonedVoice                       │
│  ✓ Generate Hindi audio using XTTS                                  │
│  ✓ Use TTS parameters (speed, temperature, repetition_penalty)      │
│  ✓ Save audio → synthesized_audio                                   │
│  Status: synthesis_status = 'synthesized'                            │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 7: ADJUST AUDIO DURATION                                      │
│  ✓ Get audio duration using ffprobe                                 │
│  ✓ Compare with video duration                                      │
│  ✓ If difference > 0.5s, adjust using ffmpeg                        │
│  ✓ Update synthesized_audio with adjusted version                   │
│  Status: Audio duration matches video                                │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 8: REMOVE ORIGINAL AUDIO                                      │
│  ✓ Use ffmpeg to remove audio from video                            │
│  ✓ Command: ffmpeg -i video.mp4 -c:v copy -an output.mp4           │
│  ✓ Save silent video → voice_removed_video                          │
│  ✓ Generate URL → voice_removed_video_url                           │
│  Status: Silent video created                                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 9: COMBINE VIDEO + TTS AUDIO                                  │
│  ✓ Use ffmpeg to merge silent video + Hindi audio                   │
│  ✓ Command: ffmpeg -i video.mp4 -i audio.wav -c:v copy -c:a aac    │
│  ✓ Ensure proper sync with -map and -shortest flags                 │
│  ✓ Save final video → final_processed_video                         │
│  ✓ Generate URL → final_processed_video_url                         │
│  Status: review_status = 'pending_review'                            │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ✅ PROCESSING COMPLETE!                           │
│                                                                      │
│  Available Downloads:                                                │
│  1. 📹 local_file_url - Original video with audio                   │
│  2. 🔇 voice_removed_video_url - Video without audio                │
│  3. 🎵 synthesized_audio_url - Hindi TTS audio                      │
│  4. ✅ final_processed_video_url - Final video with Hindi audio     │
│                                                                      │
│  Actions Available:                                                  │
│  • 🔄 Reprocess Video - Regenerate everything                       │
│  • ✏️ Review - Approve/Reject final video                           │
│  • 📥 Download - Get any of the 4 files                             │
└─────────────────────────────────────────────────────────────────────┘
```

## Error Handling at Each Step

```
┌─────────────────────────┐
│  Any Step Fails?        │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Error Handling:                                                     │
│  • Status set to 'failed'                                           │
│  • Error message saved to *_error_message field                     │
│  • Processing stops at failed step                                  │
│  • User can click "Reprocess Video" to retry                        │
│  • Reprocess resets ALL states and starts from Step 2               │
└─────────────────────────────────────────────────────────────────────┘
```

## Database Fields Updated

| Step | Fields Updated |
|------|----------------|
| 1 | `local_file`, `is_downloaded`, `duration`, `tts_speed`, `tts_temperature`, `tts_repetition_penalty` |
| 2 | `transcript`, `transcript_without_timestamps`, `transcript_language`, `transcription_status`, `transcript_processed_at` |
| 3 | `transcript_hindi` |
| 4 | `ai_summary`, `ai_tags`, `ai_processing_status`, `ai_processed_at` |
| 5 | `hindi_script`, `script_status`, `script_generated_at` |
| 6 | `synthesized_audio`, `synthesis_status` |
| 7 | `synthesized_audio` (updated with adjusted version) |
| 8 | `voice_removed_video`, `voice_removed_video_url` |
| 9 | `final_processed_video`, `final_processed_video_url`, `review_status` |

## Frontend UI States

```
┌─────────────────────────────────────────────────────────────────────┐
│  Video Detail Modal - Button Visibility                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  [Download] - Shows when: status = 'success' AND !is_downloaded     │
│                                                                      │
│  [Process Video] - Shows when: transcription_status = 'not_transcribed' │
│                    OR transcription_status = 'failed'                │
│                                                                      │
│  [Reprocess Video] - Shows when: ANY of:                            │
│    • transcription_status = 'transcribed' OR 'failed'               │
│    • script_status = 'generated' OR 'failed'                        │
│    • synthesis_status = 'synthesized' OR 'failed'                   │
│    • final_processed_video_url exists                               │
│                                                                      │
│  [Generate AI Summary] - Shows when: ai_processing_status = 'not_processed' │
│                          OR ai_processing_status = 'failed'          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Progress Indicators

```
Processing... (Auto-refetch every 2 seconds)

┌─────────────────────────────────────────────────────────────────────┐
│  ⏳ Transcribing...           [████████░░░░░░░░░░░░] 40%           │
│  ⏳ AI Processing...          [████████████░░░░░░░░] 60%           │
│  ⏳ Scripting...              [████████████████░░░░] 80%           │
│  ⏳ Generating Voice...       [████████████████████] 100%          │
│  ⏳ Removing Audio & Combining... [████████████████████] 100%      │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Technologies Used

- **Backend:** Django, Django REST Framework
- **Transcription:** Whisper (OpenAI)
- **Translation:** Google Translate API / AI Provider
- **AI Processing:** Gemini / OpenAI / Anthropic
- **TTS:** XTTS v2 (Coqui TTS)
- **Video Processing:** FFmpeg (ffprobe, audio removal, merging)
- **Frontend:** React, TanStack Query, Zustand

## Performance Notes

- **Transcription:** ~30 seconds for 1-minute video
- **AI Processing:** ~5-10 seconds
- **Script Generation:** ~5-10 seconds
- **TTS Synthesis:** ~10-30 seconds (depends on script length)
- **Video Processing:** ~10-20 seconds (depends on video size)

**Total:** ~1-2 minutes for a 1-minute video
