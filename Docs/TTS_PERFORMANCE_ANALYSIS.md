# TTS Performance Analysis - 10-Minute Video Issue

## 🔴 Critical Issues Identified

### 1. **Read Timeout (120 seconds)**

-   **Problem**: Gemini TTS API has a hardcoded 120-second timeout
-   **Impact**: For 10-minute videos with 6121 characters, the API times out before completing
-   **Location**: `legacy/root_debris/downloader/gemini_tts_service.py:149`
-   **Error**: `HTTPSConnectionPool(host='generativelanguage.googleapis.com', port=443): Read timed out. (read timeout=120)`

### 2. **No Text Chunking**

-   **Problem**: Entire text (6121 characters) is sent in a single API request
-   **Impact**:
    -   API cannot process large texts within timeout window
    -   Higher risk of rate limiting
    -   No progress tracking for long videos
-   **Location**: `legacy/root_debris/downloader/gemini_tts_service.py:115`

### 3. **Rate Limiting (429 Errors)**

-   **Problem**: Free tier quota exceeded
-   **Error**: `429 You exceeded your current quota, please check your plan and billing details`
-   **Metrics Exceeded**:
    -   `generativelanguage.googleapis.com/generate_content_free_tier_input_token_count`
    -   `generativelanguage.googleapis.com/generate_content_free_tier_requests`
-   **Impact**: Multiple retries cause quota exhaustion

## 📊 Current Behavior

For a 10-minute video:

1. **Text Length**: 6121 characters
2. **Estimated Words**: ~1000-1200 words (Hindi)
3. **Estimated Audio Duration**: ~400-480 seconds (6.5-8 minutes at 2.5 words/sec)
4. **API Timeout**: 120 seconds ❌
5. **Result**: Request times out before completion

## ✅ Solution: Implement Text Chunking

### Strategy

1. **Split text into chunks** of ~2000-2500 characters (safe for API)
2. **Generate TTS for each chunk** separately
3. **Concatenate audio files** using ffmpeg
4. **Increase timeout** per chunk (60-90 seconds per chunk)
5. **Add retry logic** with exponential backoff for rate limits
6. **Progress tracking** for frontend updates

### Implementation Plan

#### Phase 1: Chunking Logic

-   Split text at sentence boundaries (prefer `.`, `!`, `?`)
-   Target chunk size: 2000-2500 characters
-   Preserve markup tags within chunks
-   Handle edge cases (very long sentences, no punctuation)

#### Phase 2: Parallel Processing (Optional)

-   Process multiple chunks in parallel (with rate limit awareness)
-   Or sequential with progress updates

#### Phase 3: Audio Concatenation

-   Use ffmpeg to merge PCM/WAV chunks
-   Maintain audio quality
-   Handle sample rate consistency

#### Phase 4: Error Handling

-   Retry failed chunks with exponential backoff
-   Handle partial failures gracefully
-   Log progress for debugging

## 🎯 Expected Performance Improvement

**Before (Current)**:

-   10-minute video: ❌ Timeout after 120 seconds
-   Success rate: ~0% for videos > 3 minutes

**After (With Chunking)**:

-   10-minute video: ✅ ~3-5 chunks × 30-60 seconds = 2-5 minutes total
-   Success rate: ~95%+ for any video length
-   Progress tracking: Real-time updates per chunk

## 📝 Code Changes Required

1. **`gemini_tts_service.py`**:

    - Add `_chunk_text()` method
    - Modify `generate_speech()` to handle chunking
    - Add `_concatenate_audio()` method
    - Increase per-chunk timeout to 90 seconds

2. **Error Handling**:

    - Add retry logic with exponential backoff
    - Handle 429 rate limit errors gracefully
    - Log chunk progress

3. **Frontend Integration** (if needed):
    - Show progress for chunked TTS
    - Handle partial completion

## ⚠️ Rate Limit Considerations

-   **Free Tier Limits**:
    -   Requests per minute: Limited
    -   Input tokens per minute: Limited
-   **Solution**:
    -   Sequential processing with delays between chunks
    -   Or implement exponential backoff
    -   Consider upgrading to paid tier for production

---

**Status**: Analysis Complete - Ready for Implementation
**Priority**: High - Blocking long video processing
