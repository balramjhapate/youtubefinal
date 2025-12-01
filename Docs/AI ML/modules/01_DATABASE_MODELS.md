# Module 01: Database Models & Schema

## 🎯 Overview

This module defines all database models required for the analytics and automation system. It supports both **Shorts/Reels** (no thumbnails) and **Long Videos** (thumbnails required).

---

## 📋 Status

-   **Status:** ⏳ Pending
-   **Priority:** 🔴 High (Foundation Module)
-   **Dependencies:** None
-   **Estimated Time:** 2-3 days

---

## 🗄️ Database Models

### 1. Extended VideoDownload Model

**File:** `backend/downloader/models.py`

```python
class VideoDownload(models.Model):
    # ... existing fields ...

    # ========== CONTENT TYPE DETECTION ==========
    CONTENT_TYPE_CHOICES = [
        ('short', 'Short/Reel (< 3 min)'),
        ('reel', 'Reel (< 3 min)'),
        ('standard', 'Standard Video (3-10 min)'),
        ('long', 'Long Video (10+ min)'),
    ]
    content_type = models.CharField(
        max_length=20,
        choices=CONTENT_TYPE_CHOICES,
        default='short',
        help_text="Auto-detected content type"
    )

    is_short = models.BooleanField(
        default=True,
        help_text="Is this a short/reel? (no thumbnail needed)"
    )

    # ========== THUMBNAIL MANAGEMENT ==========
    # Only required for long videos
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
    thumbnail_variants = models.JSONField(
        default=list,
        help_text="A/B test thumbnail variants"
    )

    # ========== SOCIAL MEDIA UPLOAD TRACKING ==========
    # YouTube
    youtube_video_id = models.CharField(max_length=50, blank=True)
    youtube_short_id = models.CharField(max_length=50, blank=True)
    youtube_uploaded_at = models.DateTimeField(blank=True, null=True)

    # Instagram
    instagram_reel_id = models.CharField(max_length=100, blank=True)
    instagram_media_id = models.CharField(max_length=100, blank=True)
    instagram_uploaded_at = models.DateTimeField(blank=True, null=True)

    # Facebook
    facebook_post_id = models.CharField(max_length=100, blank=True)
    facebook_reel_id = models.CharField(max_length=100, blank=True)
    facebook_uploaded_at = models.DateTimeField(blank=True, null=True)

    # ========== MONETIZATION ==========
    is_monetized = models.BooleanField(default=False)
    adsense_channel_id = models.CharField(max_length=100, blank=True)

    # ========== PERFORMANCE TRACKING ==========
    total_views = models.IntegerField(default=0)
    total_engagement = models.IntegerField(default=0)
    total_revenue_usd = models.FloatField(default=0)
    average_cpm = models.FloatField(default=0)
    best_performing_keyword = models.CharField(max_length=100, blank=True)

    # ========== ML PREDICTIONS (CACHED) ==========
    ml_predicted_views_30d = models.IntegerField(default=0)
    ml_predicted_revenue_30d = models.FloatField(default=0)
    ml_confidence = models.FloatField(default=0)

    # ========== KEYWORDS ==========
    target_keywords = models.JSONField(
        default=list,
        help_text="Target keywords for SEO"
    )
    high_cpm_keywords = models.JSONField(
        default=list,
        help_text="High CPM keywords used"
    )

    def save(self, *args, **kwargs):
        """Auto-detect content type and thumbnail requirement"""
        if self.duration:
            # Shorts and Reels: Under 3 minutes (180 seconds)
            if self.duration <= 180:  # 3 minutes
                # Distinguish between short and reel based on duration
                if self.duration <= 60:
                    self.content_type = 'short'
                else:
                    self.content_type = 'reel'
                self.is_short = True
                self.thumbnail_required = False
            elif self.duration >= 600:  # 10 minutes
                self.content_type = 'long'
                self.is_short = False
                self.thumbnail_required = True
            else:
                # Standard video: 3-10 minutes
                self.content_type = 'standard'
                self.is_short = False
                self.thumbnail_required = False

        super().save(*args, **kwargs)
```

### 2. Social Media Upload Tracking

```python
class SocialMediaUpload(models.Model):
    """Track where videos are uploaded"""
    video = models.OneToOneField(
        VideoDownload,
        on_delete=models.CASCADE,
        related_name='social_upload'
    )

    # YouTube
    youtube_video_id = models.CharField(max_length=50, blank=True)
    youtube_short_id = models.CharField(max_length=50, blank=True)
    youtube_uploaded_at = models.DateTimeField(blank=True, null=True)
    youtube_status = models.CharField(
        max_length=20,
        choices=[
            ('not_uploaded', 'Not Uploaded'),
            ('uploading', 'Uploading'),
            ('uploaded', 'Uploaded'),
            ('failed', 'Failed'),
        ],
        default='not_uploaded'
    )

    # Instagram
    instagram_reel_id = models.CharField(max_length=100, blank=True)
    instagram_media_id = models.CharField(max_length=100, blank=True)
    instagram_uploaded_at = models.DateTimeField(blank=True, null=True)
    instagram_status = models.CharField(max_length=20, default='not_uploaded')

    # Facebook
    facebook_post_id = models.CharField(max_length=100, blank=True)
    facebook_reel_id = models.CharField(max_length=100, blank=True)
    facebook_uploaded_at = models.DateTimeField(blank=True, null=True)
    facebook_status = models.CharField(max_length=20, default='not_uploaded')

    class Meta:
        verbose_name = "Social Media Upload"
        verbose_name_plural = "Social Media Uploads"
```

### 3. Video Analytics Model

```python
class VideoAnalytics(models.Model):
    """Store analytics data from all platforms"""
    video = models.ForeignKey(VideoDownload, on_delete=models.CASCADE)
    platform = models.CharField(
        max_length=20,
        choices=[
            ('youtube', 'YouTube'),
            ('youtube_shorts', 'YouTube Shorts'),
            ('instagram', 'Instagram'),
            ('instagram_reels', 'Instagram Reels'),
            ('facebook', 'Facebook'),
            ('facebook_reels', 'Facebook Reels'),
        ]
    )

    # Core Metrics
    views = models.IntegerField(default=0)
    likes = models.IntegerField(default=0)
    comments = models.IntegerField(default=0)
    shares = models.IntegerField(default=0)
    saves = models.IntegerField(default=0)  # Instagram/TikTok

    # Engagement Metrics
    engagement_rate = models.FloatField(default=0)
    watch_time_minutes = models.FloatField(default=0)
    average_view_duration = models.IntegerField(default=0)

    # Shorts/Reels Specific
    completion_rate = models.FloatField(
        default=0,
        help_text="% watched to end (Shorts/Reels)"
    )
    swipe_away_rate = models.FloatField(
        default=0,
        help_text="% who swiped away (Shorts/Reels)"
    )
    rewatch_rate = models.FloatField(default=0)

    # Long Video Specific
    retention_data = models.JSONField(
        default=dict,
        help_text="Audience retention curve (Long Videos)"
    )
    average_percentage_watched = models.FloatField(
        default=0,
        help_text="Average % of video watched"
    )

    # Demographics
    demographics = models.JSONField(default=dict)
    traffic_sources = models.JSONField(default=dict)

    # Timestamps
    recorded_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['video', 'platform']
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['video', 'platform', '-recorded_at']),
        ]
```

### 4. AI Daily Report Model

```python
class AIDailyReport(models.Model):
    """AI-generated daily reports"""
    video = models.ForeignKey(VideoDownload, on_delete=models.CASCADE)
    report_date = models.DateField(default=timezone.now)

    # Report Content
    summary = models.TextField(help_text="AI-generated summary")
    insights = models.JSONField(default=list)
    recommendations = models.JSONField(default=list)
    trends = models.JSONField(default=dict)

    # Shorts/Reels Specific
    shorts_performance = models.JSONField(
        default=dict,
        help_text="Shorts-specific metrics"
    )
    viral_potential = models.FloatField(
        default=0,
        help_text="Viral potential score (0-100)"
    )

    # Long Video Specific
    retention_analysis = models.JSONField(
        default=dict,
        help_text="Retention analysis for long videos"
    )

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
    error_message = models.TextField(blank=True)

    class Meta:
        unique_together = ['video', 'report_date']
        ordering = ['-report_date']
```

### 5. ML Prediction Model

```python
class MLPrediction(models.Model):
    """ML model predictions"""
    video = models.ForeignKey(VideoDownload, on_delete=models.CASCADE)

    # Predictions
    predicted_views_7d = models.IntegerField(default=0)
    predicted_views_30d = models.IntegerField(default=0)
    predicted_engagement_rate = models.FloatField(default=0)
    predicted_revenue_30d = models.FloatField(default=0)
    predicted_optimal_post_time = models.TimeField(blank=True, null=True)

    # Confidence Scores
    confidence_score = models.FloatField(default=0)
    views_confidence = models.FloatField(default=0)
    engagement_confidence = models.FloatField(default=0)
    revenue_confidence = models.FloatField(default=0)

    # Model Info
    model_version = models.CharField(max_length=50, default='v1.0')
    model_type = models.CharField(
        max_length=20,
        choices=[
            ('regression', 'Regression'),
            ('classification', 'Classification'),
            ('ensemble', 'Ensemble'),
        ],
        default='ensemble'
    )

    # Features Used
    features_used = models.JSONField(default=dict)

    # Timestamps
    predicted_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-predicted_at']
```

### 6. Keyword Analysis Model

```python
class KeywordAnalysis(models.Model):
    """Keyword and CPM analysis"""
    video = models.ForeignKey(VideoDownload, on_delete=models.CASCADE)

    # Keywords
    primary_keywords = models.JSONField(default=list)
    high_cpm_keywords = models.JSONField(default=list)
    keyword_cpm_map = models.JSONField(default=dict)

    # Competition
    competition_level = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
        ],
        default='medium'
    )
    competition_score = models.FloatField(default=0)
    competitor_analysis = models.JSONField(default=dict)

    # Performance
    keyword_performance = models.JSONField(default=dict)

    # SEO
    seo_score = models.FloatField(default=0)
    seo_suggestions = models.JSONField(default=list)

    # Timestamps
    analyzed_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-analyzed_at']
```

### 7. AdSense Earnings Model

```python
class AdSenseEarnings(models.Model):
    """AdSense revenue tracking"""
    video = models.ForeignKey(VideoDownload, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)

    # Earnings
    revenue_usd = models.FloatField(default=0)
    estimated_revenue_usd = models.FloatField(default=0)

    # Metrics
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    ctr = models.FloatField(default=0)
    cpc = models.FloatField(default=0)
    cpm = models.FloatField(default=0)
    rpm = models.FloatField(default=0)

    # Breakdown
    ad_format_earnings = models.JSONField(default=dict)
    geographic_earnings = models.JSONField(default=dict)

    # Performance
    monetized_playbacks = models.IntegerField(default=0)
    playback_based_cpm = models.FloatField(default=0)

    # Timestamps
    recorded_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['video', 'date']
        ordering = ['-date']
```

### 8. Thumbnail Model (Long Videos)

```python
class VideoThumbnail(models.Model):
    """Thumbnails for long videos"""
    video = models.ForeignKey(VideoDownload, on_delete=models.CASCADE)

    # Thumbnail Data
    thumbnail_url = models.URLField(max_length=1000)
    thumbnail_file = models.ImageField(
        upload_to='thumbnails/',
        blank=True,
        null=True
    )

    # A/B Testing
    variant_name = models.CharField(
        max_length=50,
        default='default',
        help_text="Variant name for A/B testing"
    )
    is_active = models.BooleanField(default=True)

    # Performance
    ctr = models.FloatField(default=0)
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)

    # Generation Info
    generation_method = models.CharField(
        max_length=50,
        choices=[
            ('ai_generated', 'AI Generated'),
            ('manual', 'Manual Upload'),
            ('extracted', 'Extracted from Video'),
        ],
        default='ai_generated'
    )
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-generated_at']
```

---

## 🔄 Migrations

### Create Migrations

```bash
cd backend
python manage.py makemigrations downloader
python manage.py migrate
```

### Migration Files to Create

1. `0001_add_content_type_fields.py`
2. `0002_add_social_media_upload.py`
3. `0003_add_video_analytics.py`
4. `0004_add_ai_daily_report.py`
5. `0005_add_ml_prediction.py`
6. `0006_add_keyword_analysis.py`
7. `0007_add_adsense_earnings.py`
8. `0008_add_video_thumbnail.py`

---

## ✅ Testing

### Unit Tests

```python
# backend/downloader/tests/test_models.py

class VideoDownloadModelTest(TestCase):
    def test_content_type_detection_short(self):
        """Test auto-detection of short content (< 60s)"""
        video = VideoDownload.objects.create(
            duration=45,
            title="Test Short"
        )
        self.assertEqual(video.content_type, 'short')
        self.assertTrue(video.is_short)
        self.assertFalse(video.thumbnail_required)

    def test_content_type_detection_reel(self):
        """Test auto-detection of reel content (60s - 3 min)"""
        video = VideoDownload.objects.create(
            duration=120,  # 2 minutes
            title="Test Reel"
        )
        self.assertEqual(video.content_type, 'reel')
        self.assertTrue(video.is_short)
        self.assertFalse(video.thumbnail_required)

        # Test edge case: exactly 3 minutes (180s) should still be reel
        video2 = VideoDownload.objects.create(
            duration=180,  # Exactly 3 minutes
            title="Test Reel 3min"
        )
        self.assertEqual(video2.content_type, 'reel')
        self.assertTrue(video2.is_short)

    def test_content_type_detection_standard(self):
        """Test auto-detection of standard video (3-10 min)"""
        video = VideoDownload.objects.create(
            duration=300,  # 5 minutes
            title="Test Standard Video"
        )
        self.assertEqual(video.content_type, 'standard')
        self.assertFalse(video.is_short)
        self.assertFalse(video.thumbnail_required)

    def test_content_type_detection_long(self):
        """Test auto-detection of long content (10+ min)"""
        video = VideoDownload.objects.create(
            duration=1200,  # 20 minutes
            title="Test Long Video"
        )
        self.assertEqual(video.content_type, 'long')
        self.assertFalse(video.is_short)
        self.assertTrue(video.thumbnail_required)
```

---

## 📦 Archived Items

-   ✅ Basic VideoDownload model (existing)
-   ✅ AIProviderSettings model (existing)

---

## ⏳ Pending Items

-   [ ] Add indexes for performance
-   [ ] Add database constraints
-   [ ] Add model validation methods
-   [ ] Add admin interfaces
-   [ ] Add model signals for auto-updates

---

## 🎯 Success Criteria

-   [x] All models defined
-   [ ] Migrations created and tested
-   [ ] Unit tests passing
-   [ ] Admin interfaces configured
-   [ ] Documentation complete

---

## 📚 Next Steps

After completing this module:

1. Test all models with sample data
2. Verify migrations work correctly
3. Move to **Module 02: Social Media API Integration**
