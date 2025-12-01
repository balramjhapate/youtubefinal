# AI & ML Analytics Enhancement - Complete Implementation Guide

## 🎯 Overview

This document outlines how to integrate **AI-powered daily reports**, **ML predictions**, **keyword analysis**, and **AdSense earnings tracking** into your analytics dashboard.

---

## 🚀 New Features

### 1. **AI-Powered Daily Reports** (GPT-4o-mini or Gemini)
- Automatic analysis of each video's performance
- Daily evening reports with insights
- Actionable recommendations
- Trend analysis

### 2. **ML Models for Predictions**
- View prediction
- Engagement forecasting
- Revenue estimation
- Optimal posting time prediction
- Content performance classification

### 3. **Keyword & CPM Analysis**
- High CPM keyword research
- Competition analysis
- Keyword performance tracking
- SEO optimization suggestions

### 4. **AdSense Earnings Integration**
- Real-time revenue tracking
- Earnings per video
- CPM analysis
- Revenue optimization suggestions

---

## 📊 Database Models

### 1. AI Daily Report Model

```python
# Add to backend/downloader/models.py

class AIDailyReport(models.Model):
    """AI-generated daily reports for videos"""
    video = models.ForeignKey(VideoDownload, on_delete=models.CASCADE)
    report_date = models.DateField(default=timezone.now)
    
    # Report Content
    summary = models.TextField(help_text="AI-generated summary of performance")
    insights = models.JSONField(default=list, help_text="Key insights and observations")
    recommendations = models.JSONField(default=list, help_text="Actionable recommendations")
    trends = models.JSONField(default=dict, help_text="Trend analysis (views, engagement, etc.)")
    
    # Performance Metrics (snapshot at report time)
    views = models.IntegerField(default=0)
    engagement_rate = models.FloatField(default=0)
    watch_time_minutes = models.FloatField(default=0)
    revenue_usd = models.FloatField(default=0)
    
    # AI Model Info
    ai_model = models.CharField(max_length=50, default='gemini')  # 'gpt-4o-mini' or 'gemini'
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
        ordering = ['-report_date', '-generated_at']
        indexes = [
            models.Index(fields=['video', 'report_date']),
        ]
    
    def __str__(self):
        return f"AI Report for {self.video.title[:50]} - {self.report_date}"
```

### 2. ML Predictions Model

```python
class MLPrediction(models.Model):
    """ML model predictions for videos"""
    video = models.ForeignKey(VideoDownload, on_delete=models.CASCADE)
    
    # Predictions
    predicted_views_7d = models.IntegerField(default=0, help_text="Predicted views in 7 days")
    predicted_views_30d = models.IntegerField(default=0, help_text="Predicted views in 30 days")
    predicted_engagement_rate = models.FloatField(default=0)
    predicted_revenue_30d = models.FloatField(default=0)
    predicted_optimal_post_time = models.TimeField(blank=True, null=True)
    
    # Confidence Scores (0-1)
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
    features_used = models.JSONField(default=dict, help_text="Features used for prediction")
    
    # Timestamps
    predicted_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-predicted_at']
        indexes = [
            models.Index(fields=['video', '-predicted_at']),
        ]
```

### 3. Keyword Analysis Model

```python
class KeywordAnalysis(models.Model):
    """Keyword and CPM analysis for videos"""
    video = models.ForeignKey(VideoDownload, on_delete=models.CASCADE)
    
    # Keywords
    primary_keywords = models.JSONField(default=list, help_text="Main keywords in video")
    high_cpm_keywords = models.JSONField(default=list, help_text="High CPM keywords found")
    keyword_cpm_map = models.JSONField(default=dict, help_text="Keyword -> CPM mapping")
    
    # Competition Analysis
    competition_level = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
        ],
        default='medium'
    )
    competition_score = models.FloatField(default=0, help_text="0-1 competition score")
    competitor_analysis = models.JSONField(default=dict)
    
    # Performance
    keyword_performance = models.JSONField(
        default=dict,
        help_text="Performance metrics per keyword"
    )
    
    # SEO Metrics
    seo_score = models.FloatField(default=0, help_text="Overall SEO score 0-100")
    seo_suggestions = models.JSONField(default=list)
    
    # Timestamps
    analyzed_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-analyzed_at']
```

### 4. AdSense Earnings Model

```python
class AdSenseEarnings(models.Model):
    """AdSense revenue tracking per video"""
    video = models.ForeignKey(VideoDownload, on_delete=models.CASCADE)
    
    # Earnings Data
    date = models.DateField(default=timezone.now)
    revenue_usd = models.FloatField(default=0)
    estimated_revenue_usd = models.FloatField(default=0)  # If not yet finalized
    
    # Metrics
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    ctr = models.FloatField(default=0)  # Click-through rate
    cpc = models.FloatField(default=0)  # Cost per click
    cpm = models.FloatField(default=0)  # Cost per mille (1000 impressions)
    rpm = models.FloatField(default=0)  # Revenue per mille
    
    # Breakdown
    ad_format_earnings = models.JSONField(
        default=dict,
        help_text="Earnings by ad format (display, overlay, skippable, etc.)"
    )
    geographic_earnings = models.JSONField(
        default=dict,
        help_text="Earnings by country"
    )
    
    # Performance
    monetized_playbacks = models.IntegerField(default=0)
    playback_based_cpm = models.FloatField(default=0)
    
    # Timestamps
    recorded_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['video', 'date']
        ordering = ['-date', '-recorded_at']
        indexes = [
            models.Index(fields=['video', '-date']),
        ]
    
    def __str__(self):
        return f"${self.revenue_usd:.2f} - {self.video.title[:50]} - {self.date}"
```

### 5. Extended VideoDownload Model

```python
# Add these fields to existing VideoDownload model:

class VideoDownload(models.Model):
    # ... existing fields ...
    
    # Monetization
    is_monetized = models.BooleanField(default=False)
    adsense_channel_id = models.CharField(max_length=100, blank=True)
    
    # Keywords
    target_keywords = models.JSONField(default=list, help_text="Target keywords for SEO")
    high_cpm_keywords = models.JSONField(default=list, help_text="High CPM keywords used")
    
    # Performance Tracking
    total_revenue_usd = models.FloatField(default=0)
    average_cpm = models.FloatField(default=0)
    best_performing_keyword = models.CharField(max_length=100, blank=True)
    
    # ML Predictions (cached)
    ml_predicted_views_30d = models.IntegerField(default=0)
    ml_predicted_revenue_30d = models.FloatField(default=0)
    ml_confidence = models.FloatField(default=0)
```

---

## 🤖 AI Report Generation Service

### Implementation

```python
# backend/downloader/services/ai_report_service.py

import os
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from ..models import VideoDownload, VideoAnalytics, AIDailyReport, AdSenseEarnings

class AIReportService:
    """Generate AI-powered daily reports using GPT-4o-mini or Gemini"""
    
    def __init__(self, provider='gemini'):
        self.provider = provider
        if provider == 'gemini':
            import google.generativeai as genai
            api_key = self._get_gemini_api_key()
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        elif provider == 'gpt-4o-mini':
            from openai import OpenAI
            self.client = OpenAI(api_key=self._get_openai_api_key())
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def _get_gemini_api_key(self):
        from ..models import AIProviderSettings
        settings = AIProviderSettings.objects.first()
        if settings and settings.provider == 'gemini':
            return settings.api_key
        return os.getenv('GEMINI_API_KEY', '')
    
    def _get_openai_api_key(self):
        from ..models import AIProviderSettings
        settings = AIProviderSettings.objects.first()
        if settings and settings.provider == 'openai':
            return settings.api_key
        return os.getenv('OPENAI_API_KEY', '')
    
    def generate_daily_report(self, video_id, report_date=None):
        """Generate AI report for a video"""
        if report_date is None:
            report_date = timezone.now().date()
        
        video = VideoDownload.objects.get(id=video_id)
        
        # Check if report already exists
        existing = AIDailyReport.objects.filter(
            video=video,
            report_date=report_date
        ).first()
        
        if existing and existing.report_status == 'completed':
            return existing
        
        # Create or get pending report
        report, created = AIDailyReport.objects.get_or_create(
            video=video,
            report_date=report_date,
            defaults={'report_status': 'generating'}
        )
        
        if not created:
            report.report_status = 'generating'
            report.save()
        
        try:
            # Collect analytics data
            analytics_data = self._collect_analytics_data(video, report_date)
            
            # Generate report using AI
            report_content = self._generate_report_with_ai(video, analytics_data)
            
            # Save report
            report.summary = report_content['summary']
            report.insights = report_content['insights']
            report.recommendations = report_content['recommendations']
            report.trends = report_content['trends']
            report.views = analytics_data.get('views', 0)
            report.engagement_rate = analytics_data.get('engagement_rate', 0)
            report.watch_time_minutes = analytics_data.get('watch_time_minutes', 0)
            report.revenue_usd = analytics_data.get('revenue_usd', 0)
            report.ai_model = 'gemini-pro' if self.provider == 'gemini' else 'gpt-4o-mini'
            report.ai_provider = self.provider
            report.report_status = 'completed'
            report.save()
            
            return report
            
        except Exception as e:
            report.report_status = 'failed'
            report.error_message = str(e)
            report.save()
            raise
    
    def _collect_analytics_data(self, video, report_date):
        """Collect all analytics data for the report"""
        from ..models import VideoAnalytics, AdSenseEarnings
        
        # Get analytics from all platforms
        analytics = VideoAnalytics.objects.filter(
            video=video,
            recorded_at__date__lte=report_date
        )
        
        # Get previous day for comparison
        prev_date = report_date - timedelta(days=1)
        prev_analytics = VideoAnalytics.objects.filter(
            video=video,
            recorded_at__date=prev_date
        )
        
        # Aggregate metrics
        total_views = sum(a.views for a in analytics)
        total_engagement = sum(a.likes + a.comments + a.shares for a in analytics)
        total_watch_time = sum(a.watch_time_minutes for a in analytics)
        
        # Previous day metrics
        prev_views = sum(a.views for a in prev_analytics) if prev_analytics.exists() else 0
        
        # Calculate engagement rate
        engagement_rate = (total_engagement / total_views * 100) if total_views > 0 else 0
        
        # Get AdSense earnings
        earnings = AdSenseEarnings.objects.filter(
            video=video,
            date__lte=report_date
        ).aggregate(total_revenue=models.Sum('revenue_usd'))['total_revenue'] or 0
        
        return {
            'views': total_views,
            'prev_views': prev_views,
            'views_change': total_views - prev_views,
            'views_change_pct': ((total_views - prev_views) / prev_views * 100) if prev_views > 0 else 0,
            'engagement': total_engagement,
            'engagement_rate': engagement_rate,
            'watch_time_minutes': total_watch_time,
            'revenue_usd': earnings,
            'video_title': video.title,
            'video_duration': video.duration,
            'created_at': video.created_at,
            'platforms': list(analytics.values_list('platform', flat=True).distinct()),
        }
    
    def _generate_report_with_ai(self, video, analytics_data):
        """Generate report content using AI"""
        
        # Build prompt
        prompt = self._build_report_prompt(video, analytics_data)
        
        if self.provider == 'gemini':
            response = self.model.generate_content(prompt)
            content = response.text
        else:  # GPT-4o-mini
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert video analytics analyst. Generate detailed, actionable reports."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
            )
            content = response.choices[0].message.content
        
        # Parse AI response into structured format
        return self._parse_ai_response(content, analytics_data)
    
    def _build_report_prompt(self, video, analytics_data):
        """Build the prompt for AI analysis"""
        return f"""
Analyze the following video performance data and generate a comprehensive daily report.

VIDEO INFORMATION:
- Title: {video.title}
- Duration: {analytics_data['video_duration']} seconds
- Created: {analytics_data['created_at']}
- Platforms: {', '.join(analytics_data['platforms'])}

PERFORMANCE METRICS:
- Total Views: {analytics_data['views']:,}
- Previous Day Views: {analytics_data['prev_views']:,}
- Views Change: {analytics_data['views_change']:+,} ({analytics_data['views_change_pct']:+.1f}%)
- Engagement Rate: {analytics_data['engagement_rate']:.2f}%
- Total Watch Time: {analytics_data['watch_time_minutes']:.1f} minutes
- Revenue: ${analytics_data['revenue_usd']:.2f}

Please provide a detailed analysis in the following JSON format:
{{
    "summary": "A 2-3 sentence summary of the video's performance today",
    "insights": [
        "Key insight 1 about performance",
        "Key insight 2 about trends",
        "Key insight 3 about audience"
    ],
    "recommendations": [
        "Actionable recommendation 1",
        "Actionable recommendation 2",
        "Actionable recommendation 3"
    ],
    "trends": {{
        "views_trend": "increasing/decreasing/stable",
        "engagement_trend": "increasing/decreasing/stable",
        "revenue_trend": "increasing/decreasing/stable",
        "growth_rate": {analytics_data['views_change_pct']:.1f}
    }}
}}

Focus on:
1. What's working well
2. Areas for improvement
3. Actionable next steps
4. Comparison to previous performance
"""
    
    def _parse_ai_response(self, content, analytics_data):
        """Parse AI response into structured format"""
        import json
        import re
        
        # Try to extract JSON from response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                return {
                    'summary': parsed.get('summary', ''),
                    'insights': parsed.get('insights', []),
                    'recommendations': parsed.get('recommendations', []),
                    'trends': parsed.get('trends', {})
                }
            except json.JSONDecodeError:
                pass
        
        # Fallback: parse manually
        return {
            'summary': content[:500],
            'insights': self._extract_bullet_points(content, 'insights'),
            'recommendations': self._extract_bullet_points(content, 'recommendations'),
            'trends': {
                'views_trend': 'stable',
                'engagement_trend': 'stable',
                'revenue_trend': 'stable',
                'growth_rate': analytics_data.get('views_change_pct', 0)
            }
        }
    
    def _extract_bullet_points(self, text, section):
        """Extract bullet points from text"""
        # Simple extraction - can be improved
        lines = text.split('\n')
        points = []
        for line in lines:
            if line.strip().startswith('-') or line.strip().startswith('*'):
                points.append(line.strip()[1:].strip())
        return points[:5]  # Max 5 points


# Batch report generation for all videos
def generate_all_daily_reports(report_date=None):
    """Generate reports for all videos"""
    if report_date is None:
        report_date = timezone.now().date()
    
    service = AIReportService()
    videos = VideoDownload.objects.filter(status='success')
    
    reports = []
    for video in videos:
        try:
            report = service.generate_daily_report(video.id, report_date)
            reports.append(report)
        except Exception as e:
            print(f"Error generating report for video {video.id}: {e}")
    
    return reports
```

---

## 🧠 ML Prediction Service

```python
# backend/downloader/services/ml_prediction_service.py

import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib
import os
from django.conf import settings
from ..models import VideoDownload, VideoAnalytics, MLPrediction

class MLPredictionService:
    """ML service for video performance predictions"""
    
    def __init__(self):
        self.models = {}
        self.scaler = StandardScaler()
        self.model_dir = os.path.join(settings.BASE_DIR, 'ml_models')
        os.makedirs(self.model_dir, exist_ok=True)
        self._load_models()
    
    def _load_models(self):
        """Load trained models"""
        try:
            self.views_model = joblib.load(
                os.path.join(self.model_dir, 'views_model.pkl')
            )
            self.engagement_model = joblib.load(
                os.path.join(self.model_dir, 'engagement_model.pkl')
            )
            self.revenue_model = joblib.load(
                os.path.join(self.model_dir, 'revenue_model.pkl')
            )
        except FileNotFoundError:
            # Train models if they don't exist
            self._train_models()
    
    def _train_models(self):
        """Train ML models on historical data"""
        # Collect training data
        videos = VideoDownload.objects.filter(status='success')
        
        X = []  # Features
        y_views = []  # Target: views
        y_engagement = []  # Target: engagement rate
        y_revenue = []  # Target: revenue
        
        for video in videos:
            features = self._extract_features(video)
            if features:
                X.append(features)
                
                # Get actual outcomes
                analytics = VideoAnalytics.objects.filter(video=video)
                total_views = sum(a.views for a in analytics)
                total_engagement = sum(a.likes + a.comments + a.shares for a in analytics)
                engagement_rate = (total_engagement / total_views * 100) if total_views > 0 else 0
                
                from ..models import AdSenseEarnings
                earnings = AdSenseEarnings.objects.filter(video=video)
                total_revenue = sum(e.revenue_usd for e in earnings)
                
                y_views.append(total_views)
                y_engagement.append(engagement_rate)
                y_revenue.append(total_revenue)
        
        if len(X) < 10:  # Need at least 10 samples
            # Use default models
            self.views_model = RandomForestRegressor(n_estimators=100)
            self.engagement_model = RandomForestRegressor(n_estimators=100)
            self.revenue_model = RandomForestRegressor(n_estimators=100)
            return
        
        X = np.array(X)
        y_views = np.array(y_views)
        y_engagement = np.array(y_engagement)
        y_revenue = np.array(y_revenue)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train views model
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y_views, test_size=0.2, random_state=42
        )
        self.views_model = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1)
        self.views_model.fit(X_train, y_train)
        
        # Train engagement model
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y_engagement, test_size=0.2, random_state=42
        )
        self.engagement_model = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1)
        self.engagement_model.fit(X_train, y_train)
        
        # Train revenue model
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y_revenue, test_size=0.2, random_state=42
        )
        self.revenue_model = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1)
        self.revenue_model.fit(X_train, y_train)
        
        # Save models
        joblib.dump(self.views_model, os.path.join(self.model_dir, 'views_model.pkl'))
        joblib.dump(self.engagement_model, os.path.join(self.model_dir, 'engagement_model.pkl'))
        joblib.dump(self.revenue_model, os.path.join(self.model_dir, 'revenue_model.pkl'))
    
    def _extract_features(self, video):
        """Extract features for ML model"""
        try:
            # Video features
            duration = video.duration or 0
            title_length = len(video.title) if video.title else 0
            description_length = len(video.description) if video.description else 0
            has_transcript = 1 if video.transcript else 0
            has_ai_tags = 1 if video.ai_tags else 0
            
            # Engagement features (if available)
            analytics = VideoAnalytics.objects.filter(video=video).first()
            initial_views = analytics.views if analytics else 0
            initial_engagement = (analytics.likes + analytics.comments + analytics.shares) if analytics else 0
            
            # Keyword features
            keyword_count = len(video.target_keywords) if hasattr(video, 'target_keywords') else 0
            
            # Time features
            hour_posted = video.created_at.hour if video.created_at else 12
            day_of_week = video.created_at.weekday() if video.created_at else 0
            
            return [
                duration,
                title_length,
                description_length,
                has_transcript,
                has_ai_tags,
                initial_views,
                initial_engagement,
                keyword_count,
                hour_posted,
                day_of_week,
            ]
        except Exception as e:
            print(f"Error extracting features: {e}")
            return None
    
    def predict_video_performance(self, video_id):
        """Predict performance for a video"""
        video = VideoDownload.objects.get(id=video_id)
        
        features = self._extract_features(video)
        if not features:
            return None
        
        # Scale features
        features_scaled = self.scaler.transform([features])
        
        # Make predictions
        predicted_views_7d = max(0, int(self.views_model.predict(features_scaled)[0] * 0.25))  # 25% of 30d
        predicted_views_30d = max(0, int(self.views_model.predict(features_scaled)[0]))
        predicted_engagement_rate = max(0, self.engagement_model.predict(features_scaled)[0])
        predicted_revenue_30d = max(0, self.revenue_model.predict(features_scaled)[0])
        
        # Calculate confidence (based on model performance)
        confidence_score = 0.7  # Can be improved with actual model metrics
        
        # Save prediction
        prediction, created = MLPrediction.objects.update_or_create(
            video=video,
            defaults={
                'predicted_views_7d': predicted_views_7d,
                'predicted_views_30d': predicted_views_30d,
                'predicted_engagement_rate': predicted_engagement_rate,
                'predicted_revenue_30d': predicted_revenue_30d,
                'confidence_score': confidence_score,
                'views_confidence': confidence_score,
                'engagement_confidence': confidence_score,
                'revenue_confidence': confidence_score,
                'features_used': {
                    'duration': features[0],
                    'title_length': features[1],
                    'has_transcript': features[3],
                    'keyword_count': features[7],
                },
                'model_version': 'v1.0',
                'model_type': 'ensemble',
            }
        )
        
        # Update video with cached predictions
        video.ml_predicted_views_30d = predicted_views_30d
        video.ml_predicted_revenue_30d = predicted_revenue_30d
        video.ml_confidence = confidence_score
        video.save()
        
        return prediction
```

---

## 🔍 Keyword & CPM Analysis Service

```python
# backend/downloader/services/keyword_service.py

import requests
from ..models import VideoDownload, KeywordAnalysis

class KeywordAnalysisService:
    """Service for keyword research and CPM analysis"""
    
    def __init__(self):
        # You can integrate with:
        # - Google Keyword Planner API
        # - SEMrush API
        # - Ahrefs API
        # - YouTube Data API for keyword trends
        pass
    
    def analyze_video_keywords(self, video_id):
        """Analyze keywords for a video"""
        video = VideoDownload.objects.get(id=video_id)
        
        # Extract keywords from title, description, tags
        keywords = self._extract_keywords(video)
        
        # Get CPM data for keywords
        keyword_cpm_map = {}
        high_cpm_keywords = []
        
        for keyword in keywords:
            cpm_data = self._get_keyword_cpm(keyword)
            keyword_cpm_map[keyword] = cpm_data
            
            if cpm_data.get('cpm', 0) > 5.0:  # High CPM threshold
                high_cpm_keywords.append({
                    'keyword': keyword,
                    'cpm': cpm_data['cpm'],
                    'competition': cpm_data.get('competition', 'medium'),
                })
        
        # Analyze competition
        competition_level = self._analyze_competition(keywords)
        
        # Calculate SEO score
        seo_score = self._calculate_seo_score(video, keywords, high_cpm_keywords)
        
        # Generate SEO suggestions
        seo_suggestions = self._generate_seo_suggestions(video, keywords, high_cpm_keywords)
        
        # Save analysis
        analysis, created = KeywordAnalysis.objects.update_or_create(
            video=video,
            defaults={
                'primary_keywords': keywords[:10],  # Top 10
                'high_cpm_keywords': high_cpm_keywords,
                'keyword_cpm_map': keyword_cpm_map,
                'competition_level': competition_level,
                'competition_score': self._calculate_competition_score(competition_level),
                'seo_score': seo_score,
                'seo_suggestions': seo_suggestions,
            }
        )
        
        # Update video
        video.target_keywords = keywords[:10]
        video.high_cpm_keywords = [k['keyword'] for k in high_cpm_keywords]
        video.best_performing_keyword = high_cpm_keywords[0]['keyword'] if high_cpm_keywords else ''
        video.save()
        
        return analysis
    
    def _extract_keywords(self, video):
        """Extract keywords from video metadata"""
        keywords = []
        
        # From title
        if video.title:
            keywords.extend(self._extract_keywords_from_text(video.title))
        
        # From description
        if video.description:
            keywords.extend(self._extract_keywords_from_text(video.description))
        
        # From AI tags
        if video.ai_tags:
            tags = video.ai_tags.split(',')
            keywords.extend([tag.strip() for tag in tags])
        
        # Remove duplicates and return
        return list(set(keywords))
    
    def _extract_keywords_from_text(self, text):
        """Extract keywords from text using NLP"""
        # Simple implementation - can use NLTK or spaCy for better results
        import re
        words = re.findall(r'\b[a-z]{4,}\b', text.lower())
        # Filter common words
        stop_words = {'this', 'that', 'with', 'from', 'have', 'will', 'your', 'what', 'when', 'where'}
        keywords = [w for w in words if w not in stop_words]
        return keywords[:20]  # Top 20
    
    def _get_keyword_cpm(self, keyword):
        """Get CPM data for a keyword"""
        # This would integrate with keyword research APIs
        # For now, return mock data structure
        return {
            'keyword': keyword,
            'cpm': 3.5,  # Mock CPM
            'competition': 'medium',
            'search_volume': 10000,
            'difficulty': 45,
        }
    
    def _analyze_competition(self, keywords):
        """Analyze competition level for keywords"""
        # Simple heuristic
        if len(keywords) < 3:
            return 'low'
        elif len(keywords) < 7:
            return 'medium'
        else:
            return 'high'
    
    def _calculate_competition_score(self, level):
        """Convert competition level to score"""
        scores = {'low': 0.3, 'medium': 0.6, 'high': 0.9}
        return scores.get(level, 0.5)
    
    def _calculate_seo_score(self, video, keywords, high_cpm_keywords):
        """Calculate overall SEO score (0-100)"""
        score = 0
        
        # Has keywords (20 points)
        if keywords:
            score += 20
        
        # Has high CPM keywords (30 points)
        if high_cpm_keywords:
            score += 30
        
        # Keywords in title (20 points)
        if video.title and any(k in video.title.lower() for k in keywords[:5]):
            score += 20
        
        # Keywords in description (15 points)
        if video.description and any(k in video.description.lower() for k in keywords[:5]):
            score += 15
        
        # Has tags (15 points)
        if video.ai_tags:
            score += 15
        
        return min(100, score)
    
    def _generate_seo_suggestions(self, video, keywords, high_cpm_keywords):
        """Generate SEO optimization suggestions"""
        suggestions = []
        
        # Check title
        if not video.title or len(video.title) < 30:
            suggestions.append({
                'type': 'title',
                'message': 'Add more descriptive title (30-60 characters)',
                'priority': 'high'
            })
        
        # Check for high CPM keywords in title
        if high_cpm_keywords:
            top_cpm_keyword = high_cpm_keywords[0]['keyword']
            if not video.title or top_cpm_keyword.lower() not in video.title.lower():
                suggestions.append({
                    'type': 'keyword',
                    'message': f"Add high CPM keyword '{top_cpm_keyword}' to title",
                    'priority': 'high'
                })
        
        # Check description
        if not video.description or len(video.description) < 100:
            suggestions.append({
                'type': 'description',
                'message': 'Expand description with more keywords (200+ characters)',
                'priority': 'medium'
            })
        
        # Check tags
        if not video.ai_tags or len(video.ai_tags.split(',')) < 5:
            suggestions.append({
                'type': 'tags',
                'message': 'Add more tags (5-10 recommended)',
                'priority': 'medium'
            })
        
        return suggestions
```

---

## 💰 AdSense Integration Service

```python
# backend/downloader/services/adsense_service.py

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from ..models import VideoDownload, AdSenseEarnings

class AdSenseService:
    """Service for AdSense earnings integration"""
    
    def __init__(self, credentials_path=None):
        # Initialize AdSense API client
        # This requires OAuth setup
        pass
    
    def sync_earnings(self, video_id=None, start_date=None, end_date=None):
        """Sync AdSense earnings for videos"""
        from datetime import datetime, timedelta
        from django.utils import timezone
        
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
            
            # Fetch earnings from AdSense API
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
        # This would use AdSense Reporting API
        # Returns dict: {date: {revenue, impressions, clicks, etc.}}
        # Mock implementation
        return {}
```

---

## ⏰ Scheduled Tasks (Celery)

```python
# backend/downloader/tasks.py

from celery import shared_task
from django.utils import timezone
from datetime import time
from .services.ai_report_service import AIReportService, generate_all_daily_reports
from .services.ml_prediction_service import MLPredictionService
from .services.keyword_service import KeywordAnalysisService
from .services.adsense_service import AdSenseService
from .models import VideoDownload

@shared_task
def generate_daily_reports_evening():
    """Generate AI reports for all videos every evening"""
    # Run at 6 PM daily
    service = AIReportService()
    reports = generate_all_daily_reports()
    return f"Generated {len(reports)} reports"

@shared_task
def sync_adsense_earnings():
    """Sync AdSense earnings daily"""
    service = AdSenseService()
    service.sync_earnings()
    return "AdSense earnings synced"

@shared_task
def update_ml_predictions():
    """Update ML predictions for all videos"""
    service = MLPredictionService()
    videos = VideoDownload.objects.filter(status='success')
    
    for video in videos:
        service.predict_video_performance(video.id)
    
    return f"Updated predictions for {videos.count()} videos"

@shared_task
def analyze_keywords():
    """Analyze keywords for videos"""
    service = KeywordAnalysisService()
    videos = VideoDownload.objects.filter(status='success')
    
    for video in videos:
        service.analyze_video_keywords(video.id)
    
    return f"Analyzed keywords for {videos.count()} videos"
```

### Celery Beat Schedule

```python
# backend/rednote_project/celery.py

from celery import Celery
from celery.schedules import crontab

app = Celery('rednote_project')

app.conf.beat_schedule = {
    'generate-daily-reports': {
        'task': 'downloader.tasks.generate_daily_reports_evening',
        'schedule': crontab(hour=18, minute=0),  # 6 PM daily
    },
    'sync-adsense': {
        'task': 'downloader.tasks.sync_adsense_earnings',
        'schedule': crontab(hour=9, minute=0),  # 9 AM daily
    },
    'update-ml-predictions': {
        'task': 'downloader.tasks.update_ml_predictions',
        'schedule': crontab(hour=0, minute=0),  # Midnight daily
    },
    'analyze-keywords': {
        'task': 'downloader.tasks.analyze_keywords',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
}
```

---

## 📱 API Endpoints

```python
# Add to backend/downloader/views.py

@csrf_exempt
@require_http_methods(["GET"])
def get_ai_report(request, video_id):
    """Get AI daily report for a video"""
    from .services.ai_report_service import AIReportService
    from datetime import datetime
    
    report_date = request.GET.get('date')
    if report_date:
        report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
    
    service = AIReportService()
    report = service.generate_daily_report(video_id, report_date)
    
    return JsonResponse({
        'summary': report.summary,
        'insights': report.insights,
        'recommendations': report.recommendations,
        'trends': report.trends,
        'metrics': {
            'views': report.views,
            'engagement_rate': report.engagement_rate,
            'watch_time_minutes': report.watch_time_minutes,
            'revenue_usd': report.revenue_usd,
        },
        'generated_at': report.generated_at.isoformat(),
    })

@csrf_exempt
@require_http_methods(["GET"])
def get_ml_predictions(request, video_id):
    """Get ML predictions for a video"""
    from .services.ml_prediction_service import MLPredictionService
    
    service = MLPredictionService()
    prediction = service.predict_video_performance(video_id)
    
    if not prediction:
        return JsonResponse({'error': 'Prediction not available'}, status=404)
    
    return JsonResponse({
        'predicted_views_7d': prediction.predicted_views_7d,
        'predicted_views_30d': prediction.predicted_views_30d,
        'predicted_engagement_rate': prediction.predicted_engagement_rate,
        'predicted_revenue_30d': prediction.predicted_revenue_30d,
        'confidence_score': prediction.confidence_score,
    })

@csrf_exempt
@require_http_methods(["GET"])
def get_keyword_analysis(request, video_id):
    """Get keyword analysis for a video"""
    from .services.keyword_service import KeywordAnalysisService
    
    service = KeywordAnalysisService()
    analysis = service.analyze_video_keywords(video_id)
    
    return JsonResponse({
        'primary_keywords': analysis.primary_keywords,
        'high_cpm_keywords': analysis.high_cpm_keywords,
        'competition_level': analysis.competition_level,
        'seo_score': analysis.seo_score,
        'seo_suggestions': analysis.seo_suggestions,
    })

@csrf_exempt
@require_http_methods(["GET"])
def get_adsense_earnings(request, video_id):
    """Get AdSense earnings for a video"""
    from .models import AdSenseEarnings
    from datetime import datetime, timedelta
    
    days = int(request.GET.get('days', 30))
    start_date = timezone.now().date() - timedelta(days=days)
    
    earnings = AdSenseEarnings.objects.filter(
        video_id=video_id,
        date__gte=start_date
    ).order_by('-date')
    
    data = [{
        'date': e.date.isoformat(),
        'revenue_usd': e.revenue_usd,
        'impressions': e.impressions,
        'clicks': e.clicks,
        'cpm': e.cpm,
        'rpm': e.rpm,
    } for e in earnings]
    
    total_revenue = sum(e['revenue_usd'] for e in data)
    avg_cpm = sum(e['cpm'] for e in data) / len(data) if data else 0
    
    return JsonResponse({
        'earnings': data,
        'total_revenue': total_revenue,
        'average_cpm': avg_cpm,
        'period_days': days,
    })
```

---

## 📦 Required Packages

```bash
# Add to requirements.txt

# AI/ML
google-generativeai  # For Gemini
openai  # For GPT-4o-mini
scikit-learn  # For ML models
joblib  # For model persistence
numpy
pandas

# Background Tasks
celery
redis  # Or rabbitmq for Celery broker

# AdSense/YouTube APIs
google-api-python-client
google-auth-httplib2
google-auth-oauthlib

# Keyword Research (optional)
# semrush-api
# ahrefs-api
```

---

## 🎯 Implementation Checklist

### Week 1: Database & Models
- [ ] Add new models (AIDailyReport, MLPrediction, KeywordAnalysis, AdSenseEarnings)
- [ ] Run migrations
- [ ] Create admin interfaces

### Week 2: AI Report Service
- [ ] Implement AIReportService
- [ ] Test with Gemini
- [ ] Test with GPT-4o-mini
- [ ] Create API endpoints

### Week 3: ML Service
- [ ] Implement MLPredictionService
- [ ] Collect training data
- [ ] Train initial models
- [ ] Test predictions

### Week 4: Keyword & AdSense
- [ ] Implement KeywordAnalysisService
- [ ] Integrate AdSense API
- [ ] Test keyword analysis
- [ ] Test earnings sync

### Week 5: Scheduling & Frontend
- [ ] Set up Celery
- [ ] Configure scheduled tasks
- [ ] Create frontend components
- [ ] Build dashboard views

### Week 6: Testing & Optimization
- [ ] Test all services
- [ ] Optimize ML models
- [ ] Improve AI prompts
- [ ] Performance tuning

---

## 🎉 Result

You'll have a complete AI/ML-powered analytics system that:
- ✅ Generates daily AI reports every evening
- ✅ Predicts video performance with ML
- ✅ Analyzes keywords and CPM
- ✅ Tracks AdSense earnings
- ✅ Provides actionable insights
- ✅ Automates optimization suggestions

**This transforms your dashboard into an intelligent, data-driven content optimization platform!** 🚀

