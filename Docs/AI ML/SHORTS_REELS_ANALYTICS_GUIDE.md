# Shorts & Reels Analytics - Complete Implementation Guide

## 🎯 Overview

This guide is optimized for **Shorts and Reels** content first, with long-form videos coming later. Key difference: **Shorts/Reels don't require thumbnails** (platforms auto-generate them).

---

## 📱 Content Types

### Phase 1: Shorts & Reels (Current Focus)
- **YouTube Shorts** - < 60 seconds
- **Instagram Reels** - < 90 seconds  
- **Facebook Reels** - < 90 seconds
- **TikTok** - < 60 seconds

**Characteristics:**
- ✅ No thumbnail required (auto-generated)
- ✅ Vertical format (9:16 aspect ratio)
- ✅ Quick upload process
- ✅ Fast analytics collection

### Phase 2: Long Videos (Future)
- **YouTube Videos** - 10+ minutes
- **Instagram IGTV** - Long-form
- **Facebook Videos** - Long-form

**Characteristics:**
- ⚠️ Thumbnails required
- ⚠️ More metadata needed
- ⚠️ Different optimization strategies

---

## 📊 Database Models (Updated for Shorts/Reels)

### 1. VideoDownload Model (Extended)

```python
# Add to backend/downloader/models.py

class VideoDownload(models.Model):
    # ... existing fields ...
    
    # Content Type
    CONTENT_TYPE_CHOICES = [
        ('short', 'Short/Reel (< 60s)'),
        ('reel', 'Reel (60-90s)'),
        ('long', 'Long Video (10+ min)'),
        ('standard', 'Standard Video'),
    ]
    content_type = models.CharField(
        max_length=20,
        choices=CONTENT_TYPE_CHOICES,
        default='short',
        help_text="Type of content: short, reel, or long video"
    )
    
    # Shorts/Reels Specific
    is_short = models.BooleanField(
        default=True,
        help_text="Is this a short/reel? (no thumbnail needed)"
    )
    duration_seconds = models.IntegerField(
        default=0,
        help_text="Video duration in seconds"
    )
    
    # Thumbnail (only for long videos)
    thumbnail_required = models.BooleanField(
        default=False,
        help_text="Does this video require a custom thumbnail?"
    )
    thumbnail_url = models.URLField(
        max_length=1000,
        blank=True,
        help_text="Custom thumbnail URL (only for long videos)"
    )
    thumbnail_generated = models.BooleanField(
        default=False,
        help_text="Has thumbnail been generated?"
    )
    
    # Social Media Upload Tracking
    youtube_video_id = models.CharField(max_length=50, blank=True)
    youtube_short_id = models.CharField(max_length=50, blank=True)  # For Shorts
    instagram_reel_id = models.CharField(max_length=100, blank=True)
    facebook_reel_id = models.CharField(max_length=100, blank=True)
    
    # Upload timestamps
    youtube_uploaded_at = models.DateTimeField(blank=True, null=True)
    instagram_uploaded_at = models.DateTimeField(blank=True, null=True)
    facebook_uploaded_at = models.DateTimeField(blank=True, null=True)
    
    # Monetization (for Shorts/Reels)
    is_monetized = models.BooleanField(default=False)
    adsense_channel_id = models.CharField(max_length=100, blank=True)
    
    # Performance Tracking
    total_views = models.IntegerField(default=0)
    total_engagement = models.IntegerField(default=0)
    total_revenue_usd = models.FloatField(default=0)
    average_cpm = models.FloatField(default=0)
    
    def save(self, *args, **kwargs):
        # Auto-detect content type based on duration
        if self.duration:
            if self.duration <= 60:
                self.content_type = 'short'
                self.is_short = True
                self.thumbnail_required = False
            elif self.duration <= 90:
                self.content_type = 'reel'
                self.is_short = True
                self.thumbnail_required = False
            elif self.duration >= 600:  # 10 minutes
                self.content_type = 'long'
                self.is_short = False
                self.thumbnail_required = True
            else:
                self.content_type = 'standard'
                self.is_short = False
                self.thumbnail_required = False
        
        super().save(*args, **kwargs)
```

### 2. Shorts/Reels Analytics Model

```python
class ShortsReelsAnalytics(models.Model):
    """Analytics specific to Shorts and Reels"""
    video = models.ForeignKey(VideoDownload, on_delete=models.CASCADE)
    platform = models.CharField(
        max_length=20,
        choices=[
            ('youtube_shorts', 'YouTube Shorts'),
            ('instagram_reels', 'Instagram Reels'),
            ('facebook_reels', 'Facebook Reels'),
            ('tiktok', 'TikTok'),
        ]
    )
    
    # Core Metrics (Shorts/Reels specific)
    views = models.IntegerField(default=0)
    likes = models.IntegerField(default=0)
    comments = models.IntegerField(default=0)
    shares = models.IntegerField(default=0)
    saves = models.IntegerField(default=0)  # Instagram/TikTok
    
    # Engagement Metrics
    engagement_rate = models.FloatField(default=0)
    completion_rate = models.FloatField(default=0)  # % watched to end
    average_watch_time = models.FloatField(default=0)
    
    # Shorts/Reels Specific
    swipe_away_rate = models.FloatField(
        default=0,
        help_text="% of viewers who swiped away"
    )
    rewatch_rate = models.FloatField(
        default=0,
        help_text="% of viewers who rewatched"
    )
    
    # Revenue (if monetized)
    revenue_usd = models.FloatField(default=0)
    rpm = models.FloatField(default=0)  # Revenue per mille
    
    # Timestamps
    recorded_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['video', 'platform']
        ordering = ['-recorded_at']
```

### 3. AI Daily Report (Shorts/Reels Optimized)

```python
class AIDailyReport(models.Model):
    """AI-generated daily reports - optimized for Shorts/Reels"""
    video = models.ForeignKey(VideoDownload, on_delete=models.CASCADE)
    report_date = models.DateField(default=timezone.now)
    
    # Report Content
    summary = models.TextField(help_text="AI-generated summary")
    insights = models.JSONField(default=list)
    recommendations = models.JSONField(default=list)
    trends = models.JSONField(default=dict)
    
    # Shorts/Reels Specific Insights
    shorts_performance = models.JSONField(
        default=dict,
        help_text="Shorts-specific performance metrics"
    )
    viral_potential = models.FloatField(
        default=0,
        help_text="AI-calculated viral potential score (0-100)"
    )
    optimal_posting_time = models.TimeField(blank=True, null=True)
    
    # Performance Metrics
    views = models.IntegerField(default=0)
    engagement_rate = models.FloatField(default=0)
    completion_rate = models.FloatField(default=0)
    revenue_usd = models.FloatField(default=0)
    
    # AI Model Info
    ai_model = models.CharField(max_length=50, default='gemini')
    ai_provider = models.CharField(max_length=20, default='gemini')
    
    # Status
    generated_at = models.DateTimeField(auto_now_add=True)
    report_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('generating', 'Generating'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    
    class Meta:
        unique_together = ['video', 'report_date']
        ordering = ['-report_date']
```

---

## 🚀 Upload Service (Shorts/Reels Optimized)

### YouTube Shorts Upload

```python
# backend/downloader/services/youtube_shorts_service.py

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

class YouTubeShortsService:
    """Service for uploading YouTube Shorts (no thumbnail needed)"""
    
    def __init__(self, credentials_path):
        self.credentials = Credentials.from_authorized_user_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/youtube.upload']
        )
        self.youtube = build('youtube', 'v3', credentials=self.credentials)
    
    def upload_short(self, video_file_path, title, description, tags=None):
        """
        Upload a Short to YouTube
        
        Note: Shorts don't require thumbnails - YouTube auto-generates them
        """
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags or [],
                'categoryId': '22',  # People & Blogs
            },
            'status': {
                'privacyStatus': 'public',
                'selfDeclaredMadeForKids': False,
            }
        }
        
        # For Shorts, we add #Shorts to title/description
        if '#Shorts' not in title:
            body['snippet']['title'] = f"{title} #Shorts"
        
        if '#Shorts' not in description:
            body['snippet']['description'] = f"{description}\n\n#Shorts"
        
        # Upload video (no thumbnail)
        media = MediaFileUpload(
            video_file_path,
            chunksize=-1,
            resumable=True,
            mimetype='video/*'
        )
        
        insert_request = self.youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )
        
        response = None
        while response is None:
            status, response = insert_request.next_chunk()
            if status:
                print(f"Upload progress: {int(status.progress() * 100)}%")
        
        video_id = response['id']
        return {
            'video_id': video_id,
            'url': f"https://www.youtube.com/shorts/{video_id}",
            'title': response['snippet']['title'],
        }
    
    def get_shorts_analytics(self, video_id):
        """Get analytics for a YouTube Short"""
        # YouTube Shorts have specific analytics
        analytics = self.youtube.videos().list(
            part='statistics,contentDetails',
            id=video_id
        ).execute()
        
        if not analytics.get('items'):
            return None
        
        stats = analytics['items'][0]['statistics']
        details = analytics['items'][0]['contentDetails']
        
        return {
            'views': int(stats.get('viewCount', 0)),
            'likes': int(stats.get('likeCount', 0)),
            'comments': int(stats.get('commentCount', 0)),
            'duration': details.get('duration', 'PT0S'),
            'engagement_rate': self._calculate_engagement_rate(stats),
        }
    
    def _calculate_engagement_rate(self, stats):
        """Calculate engagement rate for Shorts"""
        views = int(stats.get('viewCount', 0))
        if views == 0:
            return 0
        
        likes = int(stats.get('likeCount', 0))
        comments = int(stats.get('commentCount', 0))
        
        engagement = likes + comments
        return (engagement / views * 100) if views > 0 else 0
```

### Instagram Reels Upload

```python
# backend/downloader/services/instagram_reels_service.py

import requests
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.instagramuser import InstagramUser
from facebook_business.adobjects.instagrammedia import InstagramMedia

class InstagramReelsService:
    """Service for uploading Instagram Reels (no thumbnail needed)"""
    
    def __init__(self, access_token, instagram_business_account_id):
        self.access_token = access_token
        self.instagram_account_id = instagram_business_account_id
        FacebookAdsApi.init(access_token=access_token)
    
    def upload_reel(self, video_file_path, caption, hashtags=None):
        """
        Upload a Reel to Instagram
        
        Note: Reels don't require thumbnails - Instagram auto-generates them
        """
        # Step 1: Initialize upload
        ig_user = InstagramUser(self.instagram_account_id)
        
        # Step 2: Upload video file
        video_response = ig_user.create_reel(
            video_url=video_file_path,  # Or upload to temporary storage first
            caption=caption,
            media_type='REELS',
        )
        
        container_id = video_response['id']
        
        # Step 3: Publish the reel
        status_response = ig_user.create_reel_publish(
            creation_id=container_id
        )
        
        media_id = status_response['id']
        
        return {
            'media_id': media_id,
            'url': f"https://www.instagram.com/reel/{media_id}/",
            'caption': caption,
        }
    
    def get_reels_analytics(self, media_id):
        """Get analytics for an Instagram Reel"""
        media = InstagramMedia(media_id)
        insights = media.get_insights(fields=[
            'impressions',
            'reach',
            'likes',
            'comments',
            'saves',
            'shares',
            'plays',
        ])
        
        data = {}
        for insight in insights:
            data[insight['name']] = insight['values'][0]['value']
        
        return {
            'views': data.get('plays', 0),
            'impressions': data.get('impressions', 0),
            'reach': data.get('reach', 0),
            'likes': data.get('likes', 0),
            'comments': data.get('comments', 0),
            'saves': data.get('saves', 0),
            'shares': data.get('shares', 0),
            'engagement_rate': self._calculate_engagement_rate(data),
        }
    
    def _calculate_engagement_rate(self, data):
        """Calculate engagement rate for Reels"""
        reach = data.get('reach', 0)
        if reach == 0:
            return 0
        
        engagement = (
            data.get('likes', 0) +
            data.get('comments', 0) +
            data.get('saves', 0) +
            data.get('shares', 0)
        )
        return (engagement / reach * 100) if reach > 0 else 0
```

### Facebook Reels Upload

```python
# backend/downloader/services/facebook_reels_service.py

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.page import Page

class FacebookReelsService:
    """Service for uploading Facebook Reels (no thumbnail needed)"""
    
    def __init__(self, access_token, page_id):
        self.access_token = access_token
        self.page_id = page_id
        FacebookAdsApi.init(access_token=access_token)
    
    def upload_reel(self, video_file_path, description, hashtags=None):
        """
        Upload a Reel to Facebook
        
        Note: Reels don't require thumbnails - Facebook auto-generates them
        """
        page = Page(self.page_id)
        
        # Upload video
        video_response = page.create_video(
            video_file=video_file_path,
            description=description,
            video_type='reels',
        )
        
        video_id = video_response['id']
        
        return {
            'video_id': video_id,
            'url': f"https://www.facebook.com/reel/{video_id}",
            'description': description,
        }
    
    def get_reels_analytics(self, video_id):
        """Get analytics for a Facebook Reel"""
        # Use Facebook Graph API
        import requests
        
        url = f"https://graph.facebook.com/v18.0/{video_id}/insights"
        params = {
            'metric': 'video_views,likes,comments,shares',
            'access_token': self.access_token,
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        return {
            'views': data.get('video_views', {}).get('value', 0),
            'likes': data.get('likes', {}).get('value', 0),
            'comments': data.get('comments', {}).get('value', 0),
            'shares': data.get('shares', {}).get('value', 0),
        }
```

---

## 🤖 AI Report Service (Shorts/Reels Optimized)

```python
# backend/downloader/services/ai_report_service.py

class AIReportService:
    """AI report service optimized for Shorts/Reels"""
    
    def _build_report_prompt(self, video, analytics_data):
        """Build prompt optimized for Shorts/Reels analysis"""
        
        content_type = "Short" if video.is_short else "Reel"
        
        return f"""
Analyze this {content_type} performance data and generate a comprehensive daily report.

VIDEO INFORMATION:
- Title: {video.title}
- Type: {content_type} ({video.duration} seconds)
- Platforms: {', '.join(analytics_data['platforms'])}

PERFORMANCE METRICS:
- Total Views: {analytics_data['views']:,}
- Engagement Rate: {analytics_data['engagement_rate']:.2f}%
- Completion Rate: {analytics_data.get('completion_rate', 0):.2f}%
- Swipe Away Rate: {analytics_data.get('swipe_away_rate', 0):.2f}%
- Revenue: ${analytics_data['revenue_usd']:.2f}

SHORTS/REELS SPECIFIC ANALYSIS:
Focus on:
1. Hook effectiveness (first 3 seconds)
2. Completion rate (did viewers watch to end?)
3. Swipe away rate (when did they leave?)
4. Viral potential (sharing, saves)
5. Optimal posting time for this type of content

Provide analysis in JSON format:
{{
    "summary": "2-3 sentence summary",
    "insights": [
        "Shorts-specific insight 1",
        "Shorts-specific insight 2",
        "Shorts-specific insight 3"
    ],
    "recommendations": [
        "Actionable recommendation for Shorts",
        "Hook improvement suggestion",
        "Posting time optimization"
    ],
    "trends": {{
        "views_trend": "increasing/decreasing/stable",
        "engagement_trend": "increasing/decreasing/stable",
        "viral_potential": 0-100 score
    }},
    "shorts_performance": {{
        "hook_effectiveness": "high/medium/low",
        "completion_rate": {analytics_data.get('completion_rate', 0)},
        "swipe_away_at": "average seconds when viewers left",
        "rewatch_rate": {analytics_data.get('rewatch_rate', 0)}
    }}
}}
"""
```

---

## 📊 Analytics Collection (Shorts/Reels Focus)

```python
# backend/downloader/services/analytics_sync_service.py

class AnalyticsSyncService:
    """Sync analytics - optimized for Shorts/Reels"""
    
    def sync_shorts_analytics(self, video_id):
        """Sync analytics for a Short/Reel"""
        video = VideoDownload.objects.get(id=video_id)
        
        if not video.is_short:
            return  # Only for Shorts/Reels
        
        analytics_data = []
        
        # YouTube Shorts
        if video.youtube_short_id:
            youtube_data = self._get_youtube_shorts_analytics(video.youtube_short_id)
            if youtube_data:
                analytics_data.append({
                    'platform': 'youtube_shorts',
                    'data': youtube_data,
                })
        
        # Instagram Reels
        if video.instagram_reel_id:
            instagram_data = self._get_instagram_reels_analytics(video.instagram_reel_id)
            if instagram_data:
                analytics_data.append({
                    'platform': 'instagram_reels',
                    'data': instagram_data,
                })
        
        # Facebook Reels
        if video.facebook_reel_id:
            facebook_data = self._get_facebook_reels_analytics(video.facebook_reel_id)
            if facebook_data:
                analytics_data.append({
                    'platform': 'facebook_reels',
                    'data': facebook_data,
                })
        
        # Save analytics
        for item in analytics_data:
            ShortsReelsAnalytics.objects.update_or_create(
                video=video,
                platform=item['platform'],
                defaults=item['data']
            )
        
        return analytics_data
```

---

## 🎯 Upload Workflow (Shorts/Reels)

```
┌─────────────────────────────────────────┐
│  Process Short/Reel                     │
│  • Download                              │
│  • Transcribe                            │
│  • AI Analysis                           │
│  • TTS (if needed)                       │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│  Upload to Platforms                    │
│  • YouTube Shorts (no thumbnail)        │
│  • Instagram Reels (no thumbnail)       │
│  • Facebook Reels (no thumbnail)        │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│  Track Analytics                        │
│  • Views, Engagement                    │
│  • Completion Rate                      │
│  • Swipe Away Rate                     │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│  AI Daily Report (6 PM)                 │
│  • Shorts-specific insights            │
│  • Hook effectiveness                  │
│  • Viral potential                     │
└─────────────────────────────────────────┘
```

---

## 📋 Key Differences: Shorts vs Long Videos

| Feature | Shorts/Reels | Long Videos |
|---------|--------------|-------------|
| **Thumbnail** | ❌ Not required | ✅ Required |
| **Upload Time** | Fast (< 1 min) | Slower (2-5 min) |
| **Metadata** | Minimal | Extensive |
| **Analytics Focus** | Completion rate, Hook | Watch time, Retention |
| **Optimization** | First 3 seconds | First 15 seconds |
| **Monetization** | Lower CPM | Higher CPM |
| **Viral Potential** | Higher | Lower |

---

## 🚀 Implementation Priority

### Phase 1: Shorts/Reels (Current)
1. ✅ Upload service (no thumbnails)
2. ✅ Analytics collection
3. ✅ AI reports (Shorts-optimized)
4. ✅ ML predictions

### Phase 2: Long Videos (Future)
1. ⏳ Thumbnail generation
2. ⏳ Extended metadata
3. ⏳ Long-form analytics
4. ⏳ Retention analysis

---

## 💡 Shorts/Reels Optimization Tips

### 1. Hook (First 3 Seconds)
- Grab attention immediately
- Show the best moment first
- Use text overlays

### 2. Completion Rate
- Keep it engaging throughout
- Use quick cuts
- Maintain energy

### 3. Posting Time
- Test different times
- Use AI to detect optimal times
- Post consistently

### 4. Hashtags
- Use trending hashtags
- Mix popular and niche
- Platform-specific strategies

---

## ✅ Checklist for Shorts/Reels

- [ ] Upload service (no thumbnails)
- [ ] Analytics collection
- [ ] AI reports (Shorts-optimized)
- [ ] Completion rate tracking
- [ ] Swipe away analysis
- [ ] Viral potential scoring
- [ ] Optimal posting time detection

---

**This implementation is optimized for Shorts and Reels first, with long videos coming later!** 🚀

