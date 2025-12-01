# Module 03: Analytics Collection Service

## 🎯 Overview

This module collects and syncs analytics data from all platforms (YouTube, Facebook, Instagram) and stores it in the database. Handles both **Shorts/Reels** and **Long Videos** with platform-specific metrics.

---

## 📋 Status

- **Status:** ⏳ Pending
- **Priority:** 🔴 High (Foundation Module)
- **Dependencies:** Module 01 (Database), Module 02 (API Integration)
- **Estimated Time:** 4-5 days

---

## 📁 File Structure

```
backend/downloader/services/
├── analytics_sync_service.py    # Main sync service
├── analytics_processor.py       # Data processing
└── analytics_calculator.py      # Metric calculations
```

---

## 🔄 Analytics Sync Service

**File:** `backend/downloader/services/analytics_sync_service.py`

```python
from django.utils import timezone
from datetime import datetime, timedelta
from ..models import VideoDownload, VideoAnalytics, SocialMediaUpload
from .youtube_service import YouTubeService
from .facebook_service import FacebookService
from .instagram_service import InstagramService

class AnalyticsSyncService:
    """Service to sync analytics from all platforms"""
    
    def __init__(self):
        self.youtube_service = YouTubeService()
        self.facebook_service = None  # Initialize with page_id
        self.instagram_service = None  # Initialize with account_id
    
    # ========== MAIN SYNC METHODS ==========
    def sync_video_analytics(self, video_id, platforms=None):
        """Sync analytics for a specific video"""
        video = VideoDownload.objects.get(id=video_id)
        
        if platforms is None:
            platforms = self._get_active_platforms(video)
        
        analytics_data = []
        
        for platform in platforms:
            try:
                if platform == 'youtube' or platform == 'youtube_shorts':
                    data = self._sync_youtube_analytics(video, platform)
                elif platform == 'facebook' or platform == 'facebook_reels':
                    data = self._sync_facebook_analytics(video, platform)
                elif platform == 'instagram' or platform == 'instagram_reels':
                    data = self._sync_instagram_analytics(video, platform)
                
                if data:
                    analytics_data.append(data)
            except Exception as e:
                print(f"Error syncing {platform} analytics: {e}")
        
        return analytics_data
    
    def sync_all_videos(self, days_back=7):
        """Sync analytics for all videos uploaded in last N days"""
        cutoff_date = timezone.now() - timedelta(days=days_back)
        videos = VideoDownload.objects.filter(
            created_at__gte=cutoff_date,
            status='success'
        )
        
        results = {
            'total': videos.count(),
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        for video in videos:
            try:
                self.sync_video_analytics(video.id)
                results['success'] += 1
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'video_id': video.id,
                    'error': str(e)
                })
        
        return results
    
    # ========== PLATFORM-SPECIFIC SYNC ==========
    def _sync_youtube_analytics(self, video, platform):
        """Sync YouTube analytics"""
        upload = video.social_upload
        
        if platform == 'youtube_shorts':
            video_id = upload.youtube_short_id
            analytics = self.youtube_service.get_shorts_analytics(video_id)
        else:
            video_id = upload.youtube_video_id
            analytics = self.youtube_service.get_video_analytics(video_id)
        
        if not analytics:
            return None
        
        # Save to database
        video_analytics, created = VideoAnalytics.objects.update_or_create(
            video=video,
            platform=platform,
            defaults={
                'views': analytics.get('views', 0),
                'likes': analytics.get('likes', 0),
                'comments': analytics.get('comments', 0),
                'shares': analytics.get('shares', 0),
                'engagement_rate': analytics.get('engagement_rate', 0),
                'watch_time_minutes': analytics.get('watch_time_minutes', 0),
                'average_view_duration': analytics.get('average_view_duration', 0),
                'completion_rate': analytics.get('completion_rate', 0) if video.is_short else 0,
                'swipe_away_rate': analytics.get('swipe_away_rate', 0) if video.is_short else 0,
                'retention_data': analytics.get('retention_data', {}) if not video.is_short else {},
                'demographics': analytics.get('demographics', {}),
                'traffic_sources': analytics.get('traffic_sources', {}),
            }
        )
        
        # Update video totals
        self._update_video_totals(video)
        
        return video_analytics
    
    def _sync_facebook_analytics(self, video, platform):
        """Sync Facebook analytics"""
        if not self.facebook_service:
            self.facebook_service = FacebookService(page_id='your_page_id')
        
        upload = video.social_upload
        
        if platform == 'facebook_reels':
            video_id = upload.facebook_reel_id
            analytics = self.facebook_service.get_reels_analytics(video_id)
        else:
            video_id = upload.facebook_post_id
            analytics = self.facebook_service.get_video_analytics(video_id)
        
        if not analytics:
            return None
        
        # Save to database
        video_analytics, created = VideoAnalytics.objects.update_or_create(
            video=video,
            platform=platform,
            defaults={
                'views': analytics.get('views', 0),
                'likes': analytics.get('reactions', 0),
                'comments': analytics.get('comments', 0),
                'shares': analytics.get('shares', 0),
                'engagement_rate': self._calculate_engagement_rate(analytics),
                'watch_time_minutes': analytics.get('avg_watch_time', 0) / 60,
                'completion_rate': analytics.get('completion_rate', 0) if video.is_short else 0,
            }
        )
        
        self._update_video_totals(video)
        return video_analytics
    
    def _sync_instagram_analytics(self, video, platform):
        """Sync Instagram analytics"""
        if not self.instagram_service:
            self.instagram_service = InstagramService(account_id='your_account_id')
        
        upload = video.social_upload
        media_id = upload.instagram_reel_id or upload.instagram_media_id
        
        if not media_id:
            return None
        
        analytics = self.instagram_service.get_reels_analytics(media_id)
        
        if not analytics:
            return None
        
        # Save to database
        video_analytics, created = VideoAnalytics.objects.update_or_create(
            video=video,
            platform=platform,
            defaults={
                'views': analytics.get('views', 0),
                'likes': analytics.get('likes', 0),
                'comments': analytics.get('comments', 0),
                'saves': analytics.get('saves', 0),
                'shares': analytics.get('shares', 0),
                'engagement_rate': analytics.get('engagement_rate', 0),
            }
        )
        
        self._update_video_totals(video)
        return video_analytics
    
    # ========== HELPER METHODS ==========
    def _get_active_platforms(self, video):
        """Get list of platforms where video is uploaded"""
        upload = video.social_upload
        platforms = []
        
        if upload.youtube_video_id or upload.youtube_short_id:
            if video.is_short and upload.youtube_short_id:
                platforms.append('youtube_shorts')
            elif not video.is_short and upload.youtube_video_id:
                platforms.append('youtube')
        
        if upload.facebook_post_id or upload.facebook_reel_id:
            if video.is_short and upload.facebook_reel_id:
                platforms.append('facebook_reels')
            elif not video.is_short and upload.facebook_post_id:
                platforms.append('facebook')
        
        if upload.instagram_reel_id or upload.instagram_media_id:
            platforms.append('instagram_reels')
        
        return platforms
    
    def _update_video_totals(self, video):
        """Update aggregated totals on video"""
        analytics = VideoAnalytics.objects.filter(video=video)
        
        video.total_views = sum(a.views for a in analytics)
        video.total_engagement = sum(
            a.likes + a.comments + a.shares for a in analytics
        )
        
        # Calculate average engagement rate
        engagement_rates = [a.engagement_rate for a in analytics if a.engagement_rate > 0]
        if engagement_rates:
            video.average_engagement_rate = sum(engagement_rates) / len(engagement_rates)
        
        video.save()
    
    def _calculate_engagement_rate(self, analytics):
        """Calculate engagement rate from analytics data"""
        views = analytics.get('views', 0) or analytics.get('reach', 0)
        if views == 0:
            return 0
        
        engagement = (
            analytics.get('likes', 0) +
            analytics.get('comments', 0) +
            analytics.get('shares', 0) +
            analytics.get('reactions', 0)
        )
        
        return (engagement / views * 100) if views > 0 else 0
```

---

## 📊 Analytics Processor

**File:** `backend/downloader/services/analytics_processor.py`

```python
from datetime import datetime, timedelta
from django.utils import timezone
from ..models import VideoAnalytics

class AnalyticsProcessor:
    """Process and calculate analytics metrics"""
    
    def calculate_trends(self, video_id, days=7):
        """Calculate trends over time"""
        cutoff_date = timezone.now() - timedelta(days=days)
        analytics = VideoAnalytics.objects.filter(
            video_id=video_id,
            recorded_at__gte=cutoff_date
        ).order_by('recorded_at')
        
        if not analytics.exists():
            return None
        
        trends = {
            'views_trend': self._calculate_trend(analytics, 'views'),
            'engagement_trend': self._calculate_trend(analytics, 'engagement_rate'),
            'growth_rate': self._calculate_growth_rate(analytics, 'views'),
        }
        
        return trends
    
    def _calculate_trend(self, analytics, field):
        """Calculate if metric is increasing, decreasing, or stable"""
        values = [getattr(a, field) for a in analytics]
        if len(values) < 2:
            return 'stable'
        
        first_half = sum(values[:len(values)//2]) / (len(values)//2)
        second_half = sum(values[len(values)//2:]) / (len(values) - len(values)//2)
        
        change = ((second_half - first_half) / first_half * 100) if first_half > 0 else 0
        
        if change > 5:
            return 'increasing'
        elif change < -5:
            return 'decreasing'
        else:
            return 'stable'
    
    def _calculate_growth_rate(self, analytics, field):
        """Calculate growth rate percentage"""
        values = [getattr(a, field) for a in analytics]
        if len(values) < 2:
            return 0
        
        first = values[0]
        last = values[-1]
        
        return ((last - first) / first * 100) if first > 0 else 0
    
    def get_comparison_data(self, video_id, comparison_period='week'):
        """Compare current period to previous period"""
        now = timezone.now()
        
        if comparison_period == 'week':
            current_start = now - timedelta(days=7)
            previous_start = now - timedelta(days=14)
            previous_end = now - timedelta(days=7)
        elif comparison_period == 'month':
            current_start = now - timedelta(days=30)
            previous_start = now - timedelta(days=60)
            previous_end = now - timedelta(days=30)
        else:
            return None
        
        current = VideoAnalytics.objects.filter(
            video_id=video_id,
            recorded_at__gte=current_start
        )
        
        previous = VideoAnalytics.objects.filter(
            video_id=video_id,
            recorded_at__gte=previous_start,
            recorded_at__lt=previous_end
        )
        
        return {
            'current': {
                'views': sum(a.views for a in current),
                'engagement': sum(a.likes + a.comments + a.shares for a in current),
            },
            'previous': {
                'views': sum(a.views for a in previous),
                'engagement': sum(a.likes + a.comments + a.shares for a in previous),
            },
            'change': self._calculate_changes(current, previous),
        }
    
    def _calculate_changes(self, current, previous):
        """Calculate percentage changes"""
        current_views = sum(a.views for a in current)
        previous_views = sum(a.views for a in previous)
        
        views_change = ((current_views - previous_views) / previous_views * 100) if previous_views > 0 else 0
        
        return {
            'views_change': views_change,
            'views_change_absolute': current_views - previous_views,
        }
```

---

## 🔢 Analytics Calculator

**File:** `backend/downloader/services/analytics_calculator.py`

```python
class AnalyticsCalculator:
    """Calculate various analytics metrics"""
    
    @staticmethod
    def calculate_engagement_rate(views, likes, comments, shares):
        """Calculate engagement rate"""
        if views == 0:
            return 0
        engagement = likes + comments + shares
        return (engagement / views * 100)
    
    @staticmethod
    def calculate_completion_rate(views, completions):
        """Calculate completion rate (for Shorts/Reels)"""
        if views == 0:
            return 0
        return (completions / views * 100)
    
    @staticmethod
    def calculate_swipe_away_rate(views, swipes):
        """Calculate swipe away rate (for Shorts/Reels)"""
        if views == 0:
            return 0
        return (swipes / views * 100)
    
    @staticmethod
    def calculate_retention_score(retention_data):
        """Calculate retention score for long videos"""
        if not retention_data:
            return 0
        
        # Average retention percentage
        retention_percentages = retention_data.get('percentages', [])
        if not retention_percentages:
            return 0
        
        return sum(retention_percentages) / len(retention_percentages)
    
    @staticmethod
    def calculate_viral_potential(views, engagement_rate, shares, saves):
        """Calculate viral potential score (0-100)"""
        # Factors:
        # - High engagement rate (40%)
        # - High share rate (30%)
        # - High save rate (20%)
        # - View growth (10%)
        
        engagement_score = min(engagement_rate / 10 * 40, 40)  # Max 40 points
        share_score = min(shares / views * 100 * 30, 30) if views > 0 else 0
        save_score = min(saves / views * 100 * 20, 20) if views > 0 else 0
        
        return engagement_score + share_score + save_score
```

---

## ✅ Testing

### Unit Tests

```python
# backend/downloader/tests/test_analytics_sync.py

class AnalyticsSyncServiceTest(TestCase):
    def setUp(self):
        self.service = AnalyticsSyncService()
        self.video = VideoDownload.objects.create(
            title="Test Video",
            duration=45,
            status='success'
        )
    
    def test_sync_video_analytics(self):
        """Test syncing analytics for a video"""
        # Mock API responses
        result = self.service.sync_video_analytics(self.video.id)
        self.assertIsNotNone(result)
    
    def test_update_video_totals(self):
        """Test updating video totals"""
        # Create analytics data
        VideoAnalytics.objects.create(
            video=self.video,
            platform='youtube_shorts',
            views=1000,
            likes=50,
            comments=10,
            shares=5
        )
        
        self.service._update_video_totals(self.video)
        self.video.refresh_from_db()
        
        self.assertEqual(self.video.total_views, 1000)
        self.assertEqual(self.video.total_engagement, 65)
```

---

## 📦 Archived Items

- ✅ Basic analytics collection structure
- ✅ Platform-specific sync methods

---

## ⏳ Pending Items

- [ ] Add caching for API responses
- [ ] Implement incremental sync (only new data)
- [ ] Add webhook support for real-time updates
- [ ] Add error recovery and retry logic
- [ ] Implement batch processing for multiple videos
- [ ] Add analytics data validation

---

## 🎯 Success Criteria

- [ ] Analytics sync working for all platforms
- [ ] Data stored correctly in database
- [ ] Video totals updated automatically
- [ ] Trends calculated correctly
- [ ] Error handling complete
- [ ] Unit tests passing

---

## 📚 Next Steps

After completing this module:
1. Test analytics collection
2. Verify data accuracy
3. Move to **Module 04: AI Daily Report Service**

