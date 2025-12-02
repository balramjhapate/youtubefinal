# Error Handling Improvements

## Summary

Improved error handling for TTS timeouts and NCA Toolkit connection failures based on analysis of Django logs (`django_20251202_143927.log`).

## Issues Identified

1. **Gemini TTS Timeout Errors** (lines 398-525 in log)
   - TTS generation timed out after 85 seconds
   - No retry logic for transient network errors
   - Error messages were not actionable

2. **NCA Toolkit Connection Failures** (lines 102, 367 in log)
   - Connection errors were logged but not well-handled
   - Error messages lacked troubleshooting suggestions
   - No distinction between different error types

## Improvements Made

### 1. Gemini TTS Service (`backend/services/gemini_tts_service.py`)

#### Added Retry Logic
- **Retry attempts**: Up to 2 retries for transient network errors
- **Exponential backoff**: Retry delay increases (2s, 4s) between attempts
- **Smart retry**: Only retries on network errors (timeout, connection), not on API errors (4xx)

#### Enhanced Error Messages
- **Timeout errors**: Now includes script length and video duration analysis
- **Connection errors**: Provides specific suggestions for troubleshooting
- **Actionable suggestions**: 
  - Suggests splitting script if >1000 characters
  - Suggests shorter scripts for videos >60 seconds
  - Reminds to check internet connection and API quota

#### Code Changes
```python
# Before: Single attempt, generic error
except requests.exceptions.ReadTimeout as e:
    raise Exception(f"TTS generation timed out...")

# After: Retry logic with detailed error messages
for attempt in range(max_retries + 1):
    try:
        response = requests.post(...)
        break
    except requests.exceptions.ReadTimeout as e:
        if attempt < max_retries:
            # Retry with exponential backoff
            time.sleep(retry_delay)
            retry_delay *= 2
            continue
        else:
            # Provide detailed error with suggestions
            raise Exception(f"TTS generation timed out after {max_retries + 1} attempts...")
```

### 2. NCA Toolkit Client (`backend/services/nca_toolkit_client.py`)

#### Enhanced Error Classification
- **Error types**: Now categorizes errors (timeout, connection, request, unknown)
- **Structured errors**: Returns error type and suggestions in response
- **Better logging**: Uses proper logging instead of print statements

#### Improved Error Messages
- **Connection errors**: Provides Docker commands to check service status
- **Timeout errors**: Explains that API may be processing large files
- **Actionable suggestions**: Includes specific commands to troubleshoot

#### Code Changes
```python
# Before: Generic error message
except requests.exceptions.ConnectionError:
    return {'success': False, 'error': 'Could not connect...'}

# After: Detailed error with suggestions
except requests.exceptions.ConnectionError as e:
    return {
        'success': False,
        'error': 'Could not connect to NCA Toolkit API...',
        'error_type': 'connection',
        'suggestion': 'Check if NCA Toolkit is running: docker ps | grep nca-toolkit...'
    }
```

### 3. Dual Transcription Service (`backend/services/dual_transcribe.py`)

#### Graceful Degradation
- **Dual mode awareness**: Knows when both NCA and Whisper are enabled
- **Non-blocking errors**: NCA failures don't block Whisper transcription in dual mode
- **Better status tracking**: Distinguishes between partial and complete failures

#### Enhanced Error Reporting
- **Error type tracking**: Preserves error type from NCA client
- **Suggestions**: Passes through troubleshooting suggestions
- **User-friendly messages**: Clear messages about what's happening and what to check

#### Code Changes
```python
# Before: Marked as failed immediately
else:
    video_download.transcription_status = 'failed'
    print(f"✗ NCA transcription failed...")

# After: Graceful handling in dual mode
else:
    if dual_transcription_enabled:
        print(f"⚠️  NCA transcription failed: {error_msg}")
        print("   Continuing with Whisper transcription...")
    else:
        video_download.transcription_status = 'failed'
        print(f"✗ NCA transcription failed: {error_msg}")
```

### 4. API Views (`backend/controller/api_views.py`)

#### Improved TTS Error Handling
- **Error categorization**: Distinguishes timeout vs connection errors
- **Helpful suggestions**: Provides context-specific advice
- **Status updates**: Broadcasts status updates via WebSocket on errors

#### Code Changes
```python
# Before: Generic error message
except Exception as e:
    error_msg = f"TTS generation failed: {str(e)}"
    logger.error(error_msg, exc_info=True)

# After: Categorized errors with suggestions
except Exception as e:
    error_str = str(e)
    if 'timed out' in error_str.lower():
        error_msg = f"TTS generation timed out: {error_str}"
        if video.duration and video.duration > 60:
            logger.info("Consider using shorter scripts for long videos.")
    elif 'connection' in error_str.lower():
        error_msg = f"TTS API connection failed: {error_str}"
        logger.info("Check your internet connection and API key configuration.")
```

## Benefits

1. **Better User Experience**
   - Clear, actionable error messages
   - Automatic retries for transient errors
   - Graceful degradation (falls back to Whisper when NCA fails)

2. **Easier Troubleshooting**
   - Specific error types help identify root causes
   - Suggestions guide users to solutions
   - Better logging for debugging

3. **Improved Reliability**
   - Retry logic handles transient network issues
   - Dual transcription ensures at least one method succeeds
   - Non-blocking errors allow pipeline to continue

4. **Better Monitoring**
   - Structured error information for logging systems
   - Error types enable better alerting
   - Detailed logs help diagnose issues

## Testing Recommendations

1. **TTS Timeout Testing**
   - Test with long scripts (>1000 characters)
   - Test with slow network connections
   - Verify retry logic works correctly

2. **NCA Connection Testing**
   - Test with NCA Toolkit stopped
   - Test with incorrect API URL
   - Verify fallback to Whisper works

3. **Dual Transcription Testing**
   - Test with both NCA and Whisper enabled
   - Test with only one enabled
   - Verify error messages are clear

## Files Modified

1. `backend/services/gemini_tts_service.py`
   - Added retry logic with exponential backoff
   - Enhanced error messages with suggestions
   - Added `time` import for retry delays

2. `backend/services/nca_toolkit_client.py`
   - Added logging support
   - Enhanced error classification
   - Added troubleshooting suggestions

3. `backend/services/dual_transcribe.py`
   - Added dual transcription mode detection
   - Improved error handling for NCA failures
   - Enhanced error messages with suggestions

4. `backend/controller/api_views.py`
   - Improved TTS error categorization
   - Added helpful suggestions for different error types
   - Enhanced WebSocket status updates

## Next Steps

1. Monitor error logs to verify improvements
2. Consider adding metrics for error rates by type
3. Add user-facing error messages in frontend
4. Consider adding automatic script splitting for long videos

