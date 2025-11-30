# Deprecated Endpoints Removal Guide

## ⚠️ Optional: Remove Deprecated Endpoints

After verifying that frontend processing works correctly, you can optionally remove the deprecated endpoints.

### Endpoints to Remove

1. **`process_ai_view()`** - Already deprecated (returns HTTP 410)
2. **`generate_audio_prompt_view()`** - May still be used, check first

### Steps to Remove

#### Step 1: Verify Frontend Doesn't Need Them

Check if frontend still calls these endpoints:
```bash
grep -r "process_ai" frontend/src/
grep -r "generate_audio_prompt" frontend/src/
```

If found, update frontend to use frontend processing instead.

#### Step 2: Remove from URLs

**File:** `backend/downloader/urls.py`

```python
# REMOVE these lines:
path('api/videos/<int:video_id>/process_ai/', views.process_ai_view, name='process_ai'),
# path('api/videos/<int:video_id>/generate_audio_prompt/', views.generate_audio_prompt_view, name='generate_audio_prompt'),  # Check if used first
```

#### Step 3: Remove from Views

**File:** `backend/downloader/views.py`

```python
# REMOVE these functions:
# def process_ai_view(request, video_id):
#     ... (entire function)

# def generate_audio_prompt_view(request, video_id):
#     ... (check if used first, then remove)
```

#### Step 4: Remove from Admin (if present)

**File:** `backend/downloader/admin.py`

Remove any references to `process_ai_view` in admin actions.

#### Step 5: Test

1. Restart backend server
2. Verify no broken imports
3. Test frontend processing still works
4. Check logs for errors

---

## ⚠️ Recommendation

**Keep deprecated endpoints for now:**
- They return helpful deprecation messages
- Frontend handles them gracefully
- No harm in keeping them
- Can be removed later after more testing

**Remove only if:**
- You're certain they're not used
- You want to clean up code
- You've tested thoroughly

---

**Status:** Optional - Not Required
**Risk:** Low (endpoints are deprecated, not broken)
**Benefit:** Cleaner codebase

