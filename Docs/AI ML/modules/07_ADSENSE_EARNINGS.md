# Module 07: AdSense Earnings Integration

## 🎯 Overview

This module integrates with Google AdSense API to track revenue, CPM, RPM, and other monetization metrics for both **Shorts/Reels** and **Long Videos**.

---

## 📋 Status

- **Status:** ⏳ Pending
- **Priority:** 🟡 Medium (Monetization)
- **Dependencies:** Module 01 (Database), Module 02 (API Integration)
- **Estimated Time:** 4-5 days

---

## 💰 Features

1. **Revenue Tracking** - Daily earnings per video
2. **CPM/RPM Analysis** - Cost per mille metrics
3. **Geographic Breakdown** - Earnings by country
4. **Ad Format Analysis** - Performance by ad type
5. **Revenue Predictions** - ML-based forecasting

---

## 📁 File Structure

```
backend/downloader/services/
└── adsense_service.py           # AdSense API integration
```

---

## 💵 AdSense Service

**File:** `backend/downloader/services/adsense_service.py`

```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from django.utils import timezone
from ..models import VideoDownload, AdSenseEarnings

class AdSenseService:
    """Service for AdSense earnings integration"""
    
    def __init__(self, credentials_path=None):
        self.credentials = self._get_credentials(credentials_path)
        if self.credentials:
            self.adsense = build('adsense', 'v2', credentials=self.credentials)
        else:
            self.adsense = None
    
    def sync_earnings(self, video_id=None, start_date=None, end_date=None):
        """Sync AdSense earnings for videos"""
        if start_date is None:
            start_date = timezone.now().date() - timedelta(days=30)
        if end_date is None:
            end_date = timezone.now().date()
        
        if video_id:
            videos = [VideoDownload.objects.get(id=video_id)]
        else:
            videos = VideoDownload.objects.filter(is_monetized=True)
        
        for video in videos:
            if not video.adsense_channel_id:
                continue
            
            earnings_data = self._fetch_adsense_data(
                video.adsense_channel_id,
                start_date,
                end_date
            )
            
            # Save earnings
            for date_str, data in earnings_data.items():
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
                AdSenseEarnings.objects.update_or_create(
                    video=video,
                    date=date,
                    defaults={
                        'revenue_usd': data.get('revenue', 0),
                        'impressions': data.get('impressions', 0),
                        'clicks': data.get('clicks', 0),
                        'ctr': data.get('ctr', 0),
                        'cpc': data.get('cpc', 0),
                        'cpm': data.get('cpm', 0),
                        'rpm': data.get('rpm', 0),
                        'monetized_playbacks': data.get('monetized_playbacks', 0),
                    }
                )
            
            # Update video totals
            total_earnings = AdSenseEarnings.objects.filter(
                video=video
            ).aggregate(total=models.Sum('revenue_usd'))['total'] or 0
            
            avg_cpm = AdSenseEarnings.objects.filter(
                video=video
            ).aggregate(avg=models.Avg('cpm'))['avg'] or 0
            
            video.total_revenue_usd = total_earnings
            video.average_cpm = avg_cpm
            video.save()
    
    def _fetch_adsense_data(self, channel_id, start_date, end_date):
        """Fetch data from AdSense API"""
        # Implementation using AdSense Reporting API
        return {}
```

---

## 📦 Archived Items

- ✅ Basic AdSense integration structure

---

## ⏳ Pending Items

- [ ] Implement AdSense Reporting API
- [ ] Add geographic breakdown
- [ ] Add ad format analysis
- [ ] Implement revenue forecasting
- [ ] Add earnings alerts

---

## 🎯 Success Criteria

- [ ] AdSense earnings syncing
- [ ] CPM/RPM calculated
- [ ] Revenue tracking working
- [ ] Unit tests passing

---

## 📚 Next Steps

After completing this module:
1. Test AdSense integration
2. Verify earnings accuracy
3. Move to **Module 08: Upload Services**

