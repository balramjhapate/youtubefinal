# Module 02: Social Media API Integration

## 🎯 Overview

This module integrates with YouTube, Facebook, and Instagram APIs to fetch analytics data and manage uploads. Supports both **Shorts/Reels** and **Long Videos**.

---

## 📋 Status

- **Status:** ⏳ Pending
- **Priority:** 🔴 High (Foundation Module)
- **Dependencies:** Module 01 (Database Models)
- **Estimated Time:** 5-7 days

---

## 🔌 API Integrations Required

### 1. YouTube Data API v3
- **Purpose:** Analytics, Upload, Metadata
- **Scopes:** `youtube.readonly`, `youtube.upload`, `youtube.force-ssl`
- **Rate Limit:** 10,000 units/day
- **Documentation:** https://developers.google.com/youtube/v3

### 2. Facebook Graph API
- **Purpose:** Analytics, Upload, Page Management
- **Scopes:** `pages_read_engagement`, `pages_manage_posts`, `pages_read_user_content`
- **Rate Limit:** 200 calls/hour/user
- **Documentation:** https://developers.facebook.com/docs/graph-api

### 3. Instagram Graph API
- **Purpose:** Reels Analytics, Upload
- **Scopes:** `instagram_basic`, `instagram_content_publish`, `pages_read_engagement`
- **Rate Limit:** 200 calls/hour/user
- **Documentation:** https://developers.facebook.com/docs/instagram-api

---

## 📁 File Structure

```
backend/downloader/services/
├── __init__.py
├── youtube_service.py          # YouTube API client
├── facebook_service.py          # Facebook API client
├── instagram_service.py         # Instagram API client
└── api_auth_service.py          # OAuth & token management
```

---

## 🔐 Authentication Service

**File:** `backend/downloader/services/api_auth_service.py`

```python
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from facebook_business.api import FacebookAdsApi
import os
from django.conf import settings

class APIAuthService:
    """Manage OAuth tokens for all platforms"""
    
    def __init__(self):
        self.youtube_credentials = None
        self.facebook_token = None
        self.instagram_token = None
    
    # ========== YOUTUBE AUTH ==========
    def get_youtube_credentials(self):
        """Get YouTube OAuth credentials"""
        # Load from database or environment
        creds_path = os.path.join(settings.BASE_DIR, 'credentials', 'youtube_credentials.json')
        if os.path.exists(creds_path):
            return Credentials.from_authorized_user_file(creds_path)
        return None
    
    def refresh_youtube_token(self, credentials):
        """Refresh YouTube access token"""
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        return credentials
    
    # ========== FACEBOOK AUTH ==========
    def get_facebook_token(self):
        """Get Facebook access token"""
        # Load from database or environment
        return os.getenv('FACEBOOK_ACCESS_TOKEN', '')
    
    def initialize_facebook_api(self, access_token):
        """Initialize Facebook API"""
        FacebookAdsApi.init(access_token=access_token)
        return FacebookAdsApi.get_default_api()
    
    # ========== INSTAGRAM AUTH ==========
    def get_instagram_token(self):
        """Get Instagram access token"""
        # Instagram uses Facebook token
        return self.get_facebook_token()
```

---

## 📺 YouTube Service

**File:** `backend/downloader/services/youtube_service.py`

```python
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .api_auth_service import APIAuthService

class YouTubeService:
    """YouTube API service for analytics and uploads"""
    
    def __init__(self):
        self.auth_service = APIAuthService()
        self.credentials = self.auth_service.get_youtube_credentials()
        if self.credentials:
            self.youtube = build('youtube', 'v3', credentials=self.credentials)
        else:
            self.youtube = None
    
    # ========== ANALYTICS ==========
    def get_video_analytics(self, video_id, start_date=None, end_date=None):
        """Get analytics for a YouTube video"""
        if not self.youtube:
            return None
        
        try:
            # Get video statistics
            video_response = self.youtube.videos().list(
                part='statistics,contentDetails,snippet',
                id=video_id
            ).execute()
            
            if not video_response.get('items'):
                return None
            
            video = video_response['items'][0]
            stats = video['statistics']
            details = video['contentDetails']
            
            # Get analytics data (requires YouTube Analytics API)
            analytics_data = self._get_analytics_data(video_id, start_date, end_date)
            
            return {
                'views': int(stats.get('viewCount', 0)),
                'likes': int(stats.get('likeCount', 0)),
                'comments': int(stats.get('commentCount', 0)),
                'duration': details.get('duration', 'PT0S'),
                'engagement_rate': self._calculate_engagement_rate(stats),
                'analytics': analytics_data,
            }
        except HttpError as e:
            print(f"YouTube API Error: {e}")
            return None
    
    def get_shorts_analytics(self, video_id):
        """Get analytics specifically for YouTube Shorts"""
        analytics = self.get_video_analytics(video_id)
        if analytics:
            # Add Shorts-specific metrics
            analytics['completion_rate'] = self._get_completion_rate(video_id)
            analytics['swipe_away_rate'] = self._get_swipe_away_rate(video_id)
        return analytics
    
    def _get_analytics_data(self, video_id, start_date, end_date):
        """Get detailed analytics from YouTube Analytics API"""
        # This requires YouTube Analytics API
        # Returns: watch time, retention, demographics, etc.
        return {}
    
    def _calculate_engagement_rate(self, stats):
        """Calculate engagement rate"""
        views = int(stats.get('viewCount', 0))
        if views == 0:
            return 0
        
        likes = int(stats.get('likeCount', 0))
        comments = int(stats.get('commentCount', 0))
        engagement = likes + comments
        
        return (engagement / views * 100) if views > 0 else 0
    
    # ========== UPLOAD ==========
    def upload_video(self, video_file_path, metadata, is_short=False):
        """Upload video to YouTube"""
        from googleapiclient.http import MediaFileUpload
        
        if not self.youtube:
            return None
        
        body = {
            'snippet': {
                'title': metadata.get('title', ''),
                'description': metadata.get('description', ''),
                'tags': metadata.get('tags', []),
                'categoryId': metadata.get('category_id', '22'),
            },
            'status': {
                'privacyStatus': metadata.get('privacy', 'public'),
                'selfDeclaredMadeForKids': False,
            }
        }
        
        # Add #Shorts tag for shorts
        if is_short:
            if '#Shorts' not in body['snippet']['title']:
                body['snippet']['title'] = f"{body['snippet']['title']} #Shorts"
            if '#Shorts' not in body['snippet']['description']:
                body['snippet']['description'] = f"{body['snippet']['description']}\n\n#Shorts"
        
        # Upload video
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
        
        return {
            'video_id': response['id'],
            'url': f"https://www.youtube.com/watch?v={response['id']}",
            'title': response['snippet']['title'],
        }
    
    def upload_thumbnail(self, video_id, thumbnail_path):
        """Upload custom thumbnail (only for long videos)"""
        if not self.youtube:
            return None
        
        try:
            self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            ).execute()
            return True
        except HttpError as e:
            print(f"Thumbnail upload error: {e}")
            return False
```

---

## 📘 Facebook Service

**File:** `backend/downloader/services/facebook_service.py`

```python
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.page import Page
from facebook_business.adobjects.video import Video
from .api_auth_service import APIAuthService

class FacebookService:
    """Facebook Graph API service"""
    
    def __init__(self, page_id):
        self.auth_service = APIAuthService()
        self.access_token = self.auth_service.get_facebook_token()
        self.page_id = page_id
        
        if self.access_token:
            FacebookAdsApi.init(access_token=self.access_token)
            self.page = Page(page_id)
        else:
            self.page = None
    
    # ========== ANALYTICS ==========
    def get_video_analytics(self, video_id):
        """Get analytics for a Facebook video"""
        if not self.page:
            return None
        
        try:
            video = Video(video_id)
            insights = video.get_insights(fields=[
                'video_views',
                'video_views_unique',
                'video_avg_time_watched',
                'video_complete_views',
                'reactions_total',
                'comments',
                'shares',
            ])
            
            data = {}
            for insight in insights:
                data[insight['name']] = insight['values'][0]['value']
            
            return {
                'views': data.get('video_views', 0),
                'unique_views': data.get('video_views_unique', 0),
                'avg_watch_time': data.get('video_avg_time_watched', 0),
                'complete_views': data.get('video_complete_views', 0),
                'reactions': data.get('reactions_total', 0),
                'comments': data.get('comments', 0),
                'shares': data.get('shares', 0),
            }
        except Exception as e:
            print(f"Facebook API Error: {e}")
            return None
    
    def get_reels_analytics(self, reel_id):
        """Get analytics for Facebook Reels"""
        analytics = self.get_video_analytics(reel_id)
        if analytics:
            # Add Reels-specific metrics
            analytics['completion_rate'] = self._calculate_completion_rate(analytics)
        return analytics
    
    # ========== UPLOAD ==========
    def upload_video(self, video_file_path, description, is_reel=False):
        """Upload video to Facebook"""
        if not self.page:
            return None
        
        try:
            if is_reel:
                # Upload as Reel
                video_response = self.page.create_video(
                    video_file=video_file_path,
                    description=description,
                    video_type='reels',
                )
            else:
                # Upload as regular video
                video_response = self.page.create_video(
                    video_file=video_file_path,
                    description=description,
                )
            
            return {
                'video_id': video_response['id'],
                'url': f"https://www.facebook.com/{self.page_id}/videos/{video_response['id']}",
            }
        except Exception as e:
            print(f"Facebook upload error: {e}")
            return None
```

---

## 📷 Instagram Service

**File:** `backend/downloader/services/instagram_service.py`

```python
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.instagramuser import InstagramUser
from facebook_business.adobjects.instagrammedia import InstagramMedia
from .api_auth_service import APIAuthService

class InstagramService:
    """Instagram Graph API service"""
    
    def __init__(self, instagram_business_account_id):
        self.auth_service = APIAuthService()
        self.access_token = self.auth_service.get_instagram_token()
        self.instagram_account_id = instagram_business_account_id
        
        if self.access_token:
            FacebookAdsApi.init(access_token=self.access_token)
            self.ig_user = InstagramUser(instagram_business_account_id)
        else:
            self.ig_user = None
    
    # ========== ANALYTICS ==========
    def get_reels_analytics(self, media_id):
        """Get analytics for Instagram Reels"""
        if not self.ig_user:
            return None
        
        try:
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
        except Exception as e:
            print(f"Instagram API Error: {e}")
            return None
    
    # ========== UPLOAD ==========
    def upload_reel(self, video_file_path, caption, hashtags=None):
        """Upload Reel to Instagram"""
        if not self.ig_user:
            return None
        
        try:
            # Step 1: Initialize upload
            video_response = self.ig_user.create_reel(
                video_url=video_file_path,  # Or upload to temp storage first
                caption=caption,
                media_type='REELS',
            )
            
            container_id = video_response['id']
            
            # Step 2: Publish
            status_response = self.ig_user.create_reel_publish(
                creation_id=container_id
            )
            
            return {
                'media_id': status_response['id'],
                'url': f"https://www.instagram.com/reel/{status_response['id']}/",
            }
        except Exception as e:
            print(f"Instagram upload error: {e}")
            return None
```

---

## ✅ Testing

### Unit Tests

```python
# backend/downloader/tests/test_api_integration.py

class YouTubeServiceTest(TestCase):
    def setUp(self):
        self.service = YouTubeService()
    
    def test_get_video_analytics(self):
        """Test fetching video analytics"""
        analytics = self.service.get_video_analytics('test_video_id')
        self.assertIsNotNone(analytics)
        self.assertIn('views', analytics)
        self.assertIn('likes', analytics)
```

---

## 📦 Archived Items

- ✅ Basic API client structure
- ✅ OAuth flow documentation

---

## ⏳ Pending Items

- [ ] Implement token refresh logic
- [ ] Add error handling and retries
- [ ] Add rate limiting
- [ ] Add caching for API responses
- [ ] Implement batch requests
- [ ] Add webhook support for real-time updates

---

## 🎯 Success Criteria

- [ ] All API services implemented
- [ ] OAuth authentication working
- [ ] Analytics fetching working
- [ ] Upload functionality working
- [ ] Error handling complete
- [ ] Unit tests passing

---

## 📚 Next Steps

After completing this module:
1. Test API connections
2. Verify OAuth flows
3. Move to **Module 03: Analytics Collection Service**

