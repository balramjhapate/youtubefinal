# Module 11: Background Tasks & Scheduling

## 🎯 Overview

This module sets up Celery for background task processing and scheduled jobs. Handles daily reports, analytics sync, ML predictions, and other automated tasks.

---

## 📋 Status

- **Status:** ⏳ Pending
- **Priority:** 🔴 High (Infrastructure)
- **Dependencies:** All service modules
- **Estimated Time:** 3-4 days

---

## ⏰ Scheduled Tasks

1. **Daily AI Reports** - 6:00 PM daily
2. **Analytics Sync** - Every hour
3. **ML Predictions** - 12:00 AM daily
4. **Keyword Analysis** - 2:00 AM daily
5. **AdSense Sync** - 9:00 AM daily

---

## 📁 File Structure

```
backend/downloader/
├── tasks.py                     # Celery tasks
└── rednote_project/
    └── celery.py                # Celery configuration
```

---

## ⏰ Celery Tasks

**File:** `backend/downloader/tasks.py`

```python
from celery import shared_task
from django.utils import timezone
from datetime import time
from .services.ai_report_service import AIReportService
from .services.analytics_sync_service import AnalyticsSyncService
from .services.ml_prediction_service import MLPredictionService
from .services.keyword_analysis_service import KeywordAnalysisService
from .services.adsense_service import AdSenseService

@shared_task
def generate_daily_reports_evening():
    """Generate AI reports for all videos every evening at 6 PM"""
    service = AIReportService()
    reports = service.generate_all_daily_reports()
    return f"Generated {len(reports)} reports"

@shared_task
def sync_analytics_hourly():
    """Sync analytics every hour"""
    service = AnalyticsSyncService()
    results = service.sync_all_videos(days_back=1)
    return f"Synced {results['success']} videos"

@shared_task
def update_ml_predictions():
    """Update ML predictions daily at midnight"""
    service = MLPredictionService()
    videos = VideoDownload.objects.filter(status='success')
    
    for video in videos:
        service.predict_video_performance(video.id)
    
    return f"Updated predictions for {videos.count()} videos"

@shared_task
def analyze_keywords():
    """Analyze keywords daily at 2 AM"""
    service = KeywordAnalysisService()
    videos = VideoDownload.objects.filter(status='success')
    
    for video in videos:
        service.analyze_video_keywords(video.id)
    
    return f"Analyzed keywords for {videos.count()} videos"

@shared_task
def sync_adsense_earnings():
    """Sync AdSense earnings daily at 9 AM"""
    service = AdSenseService()
    service.sync_earnings()
    return "AdSense earnings synced"
```

---

## 📦 Archived Items

- ✅ Basic Celery setup

---

## ⏳ Pending Items

- [ ] Set up Celery with Redis
- [ ] Configure scheduled tasks
- [ ] Add task monitoring
- [ ] Implement error handling
- [ ] Add task retry logic

---

## 🎯 Success Criteria

- [ ] Celery configured and running
- [ ] All scheduled tasks working
- [ ] Tasks executing on time
- [ ] Error handling complete
- [ ] Monitoring in place

---

## 📚 Next Steps

After completing this module:
1. Test all scheduled tasks
2. Verify task execution
3. Move to **Module 12: Frontend Components**

