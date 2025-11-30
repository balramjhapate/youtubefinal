# URL Routing Fix - update_status Endpoint

## Issue
The `/api/videos/<video_id>/update_status/` endpoint was returning 404 errors.

## Root Cause
Django URL patterns are matched in order, and the first match wins. The generic pattern:
```python
path('api/videos/<int:video_id>/', views.get_video, name='get_video')
```
was matching `/api/videos/39/update_status/` before the more specific pattern:
```python
path('api/videos/<int:video_id>/update_status/', views.update_video_status, name='update_video_status')
```
could match it.

## Solution
Reordered the URL patterns so that **specific patterns come before generic patterns**.

### Before (Incorrect Order):
```python
path('api/videos/<int:video_id>/', views.get_video, name='get_video'),  # Generic - matches everything
path('api/videos/<int:video_id>/update_status/', views.update_video_status, name='update_video_status'),  # Specific - never reached
```

### After (Correct Order):
```python
path('api/videos/<int:video_id>/update_status/', views.update_video_status, name='update_video_status'),  # Specific - matches first
path('api/videos/<int:video_id>/upload_audio/', views.upload_synthesized_audio_view, name='upload_synthesized_audio'),  # Specific
path('api/videos/<int:video_id>/delete/', views.delete_video, name='delete_video'),  # Specific
path('api/videos/<int:video_id>/reprocess/', views.reprocess_video, name='reprocess_video'),  # Specific
path('api/videos/<int:video_id>/', views.get_video, name='get_video'),  # Generic - catch-all (must be last)
```

## Action Required
**Restart the Django server** for the URL changes to take effect:

```bash
# Stop the current server (Ctrl+C)
# Then restart:
cd backend
python manage.py runserver
```

## Verification
After restarting, test the endpoint:
```bash
curl -X POST http://localhost:8000/api/videos/39/update_status/ \
  -H "Content-Type: application/json" \
  -d '{"transcript_hindi": "test"}'
```

Should return: `{"status": "updated"}`

---

**Status:** Fixed
**Date:** 2024

