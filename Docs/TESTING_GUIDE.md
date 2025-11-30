# Frontend Migration Testing Guide

## 🧪 Testing Checklist

### Pre-Testing Setup

1. **Backend Setup:**
   ```bash
   cd backend
   python manage.py migrate
   python manage.py runserver
   ```

2. **Frontend Setup:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Verify Services:**
   - Backend running on http://localhost:8000
   - Frontend running on http://localhost:5173 (or configured port)
   - Database accessible
   - AI API keys configured in Settings

---

## Phase 1: Translation Migration Testing

### Test 1: Auto-Translation After Transcription
1. Extract a video (or use existing video with transcript)
2. Wait for transcription to complete
3. **Expected:** Frontend automatically translates transcript to Hindi
4. **Verify:**
   - Check browser console for "Translating to Hindi..." message
   - Check `transcript_hindi` field in database
   - Verify translation appears in UI

### Test 2: Translation Service Direct Test
1. Open browser console
2. Run:
   ```javascript
   import { translateText } from './services/translation';
   translateText("Hello world", "hi").then(console.log);
   ```
3. **Expected:** Returns Hindi translation

### Test 3: Backend No Translation
1. Check backend logs during transcription
2. **Expected:** No translation happening in backend
3. **Verify:** Backend only does transcription, no translation calls

---

## Phase 2: AI Processing Migration Testing

### Test 1: Auto-AI Processing After Transcription
1. Extract a video (or use existing video with transcript)
2. Wait for transcription to complete
3. **Expected:** Frontend automatically processes with AI (parallel with translation)
4. **Verify:**
   - Check browser console for AI processing messages
   - Check `ai_summary` and `ai_tags` fields in database
   - Verify AI results appear in UI

### Test 2: AI Processing Service Direct Test
1. Open browser console
2. Run:
   ```javascript
   import { generateSummary } from './services/aiProcessing';
   generateSummary("test transcript", "test title", "test description", "gemini", "api_key").then(console.log);
   ```
3. **Expected:** Returns summary and tags

### Test 3: Deprecated Endpoint Test
1. Call deprecated endpoint:
   ```bash
   curl -X POST http://localhost:8000/api/videos/1/process_ai/
   ```
2. **Expected:** Returns HTTP 410 with deprecation message
3. **Verify:** Message directs to frontend processing

### Test 4: Backend No AI Processing
1. Check backend logs during transcription
2. **Expected:** No AI processing happening in backend
3. **Verify:** Backend only does transcription, no AI calls

---

## Phase 3: Script Generation Migration Testing

### Test 1: Auto-Script Generation After AI Processing
1. Extract a video (or use existing video)
2. Wait for transcription → translation + AI processing to complete
3. **Expected:** Frontend automatically generates Hindi script
4. **Verify:**
   - Check browser console for script generation messages
   - Check `hindi_script` field in database
   - Verify script appears in UI
   - Verify script starts with "देखो"
   - Verify script ends with CTA

### Test 2: Script Generation Service Direct Test
1. Open browser console
2. Run:
   ```javascript
   import { generateHindiScript } from './services/scriptGenerator';
   generateHindiScript("transcript", "hindi transcript", "title", "description", 30, "gemini", "api_key").then(console.log);
   ```
3. **Expected:** Returns formatted Hindi script

### Test 3: Text Processing Utilities Test
1. Open browser console
2. Run:
   ```javascript
   import { cleanScriptForTTS, removeTimestamps } from './utils/textProcessing';
   console.log(cleanScriptForTTS("test script"));
   console.log(removeTimestamps("00:00:10 test text"));
   ```
3. **Expected:** Returns cleaned text

### Test 4: Backend No Script Generation
1. Check backend logs during transcription
2. **Expected:** No script generation happening in backend
3. **Verify:** Backend only does transcription, no script generation calls

---

## Phase 4: Text Processing Migration Testing

### Test 1: Text Processing Functions
1. Test all text processing utilities:
   - `removeTimestamps()`
   - `removeNonHindiCharacters()`
   - `fixSentenceStructure()`
   - `formatHindiScript()`
   - `cleanScriptForTTS()`
   - `filterSubscribeMentions()`
2. **Expected:** All functions work correctly

### Test 2: Integration Test
1. Generate a script
2. Clean it for TTS
3. **Expected:** Script is properly cleaned

---

## Phase 5: Backend Cleanup Verification

### Test 1: Backend Logs Check
1. Start backend server
2. Extract and process a video
3. **Check logs for:**
   - ✅ Transcription messages
   - ✅ "Translation will be handled by frontend" messages
   - ✅ "AI processing will be handled by frontend" messages
   - ✅ "Script generation will be handled by frontend" messages
   - ❌ No translation calls
   - ❌ No AI processing calls
   - ❌ No script generation calls

### Test 2: Endpoint Verification
1. Test transcription endpoint:
   ```bash
   curl -X POST http://localhost:8000/api/videos/1/transcribe/
   ```
2. **Expected:** Transcription works, no translation in response

### Test 3: Status Update Endpoint
1. Test status update endpoint:
   ```bash
   curl -X POST http://localhost:8000/api/videos/1/update_status/ \
     -H "Content-Type: application/json" \
     -d '{"transcript_hindi": "test", "ai_summary": "test", "hindi_script": "test"}'
   ```
2. **Expected:** Status updated successfully

---

## End-to-End Testing

### Full Pipeline Test
1. **Extract Video:**
   - Extract a new video
   - **Expected:** Video extracted, title/description translated (backend)

2. **Transcription:**
   - Wait for transcription
   - **Expected:** Transcript generated (backend)

3. **Frontend Processing:**
   - **Expected:** Translation happens automatically (frontend)
   - **Expected:** AI processing happens automatically (frontend, parallel)
   - **Expected:** Script generation happens automatically (frontend, after AI)

4. **Verify Results:**
   - Check database for all fields populated
   - Check UI for all data displayed
   - Check browser console for no errors

### Performance Test
1. Time the full processing:
   - **Old Backend:** ~13-25 seconds
   - **New Frontend:** ~4-10 seconds
2. **Expected:** Significant speed improvement

---

## Error Handling Tests

### Test 1: Missing API Keys
1. Remove AI API key from Settings
2. Process a video
3. **Expected:** Frontend skips AI processing gracefully, no crashes

### Test 2: Network Errors
1. Disconnect network during processing
2. **Expected:** Frontend handles errors gracefully, shows error messages

### Test 3: Invalid Data
1. Send invalid data to status update endpoint
2. **Expected:** Backend validates and returns error

---

## Browser Console Monitoring

### What to Look For:
- ✅ "Translating to Hindi..." messages
- ✅ "AI processing..." messages
- ✅ "Generating Hindi script..." messages
- ✅ "Translation Complete" messages
- ✅ "AI processing completed" messages
- ✅ "Script generation completed" messages
- ❌ No errors
- ❌ No failed API calls

---

## Backend Log Monitoring

### What to Look For:
- ✅ Transcription messages
- ✅ "Translation will be handled by frontend" messages
- ✅ "AI processing will be handled by frontend" messages
- ✅ "Script generation will be handled by frontend" messages
- ❌ No translation function calls
- ❌ No AI processing function calls
- ❌ No script generation function calls

---

## Database Verification

### Check These Fields:
- `transcript` - Should be populated by backend
- `transcript_hindi` - Should be populated by frontend
- `ai_summary` - Should be populated by frontend
- `ai_tags` - Should be populated by frontend
- `hindi_script` - Should be populated by frontend
- `transcription_status` - Should be "transcribed" (backend)
- `ai_processing_status` - Should be "processed" (frontend)
- `script_status` - Should be "generated" (frontend, if legacy model)

---

## Rollback Plan

If issues are found:
1. Check git commit history
2. Revert changes if needed
3. Report issues with:
   - Browser console errors
   - Backend log errors
   - Database state
   - Steps to reproduce

---

## Success Criteria

✅ All tests pass
✅ No errors in browser console
✅ No errors in backend logs
✅ All data populated correctly
✅ Performance improvement verified
✅ User experience improved

---

**Status:** Ready for Testing
**Date:** 2024

