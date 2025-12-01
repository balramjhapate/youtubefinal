# Module 04: AI Daily Report Service

## 🎯 Overview

This module generates AI-powered daily reports for each video using GPT-4o-mini or Gemini. Reports include insights, recommendations, and trends optimized for both **Shorts/Reels** and **Long Videos**.

---

## 📋 Status

- **Status:** ⏳ Pending
- **Priority:** 🟡 Medium (Core Intelligence)
- **Dependencies:** Module 01 (Database), Module 03 (Analytics)
- **Estimated Time:** 5-6 days

---

## 🤖 AI Providers

### Supported Providers
1. **Gemini** (Google) - Default, free tier available
2. **GPT-4o-mini** (OpenAI) - Cost-effective, fast

### Provider Selection
- Configurable via `AIProviderSettings` model
- Can switch between providers
- Fallback mechanism if one fails

---

## 📁 File Structure

```
backend/downloader/services/
├── ai_report_service.py         # Main report generation
├── ai_prompt_builder.py         # Build AI prompts
└── ai_response_parser.py        # Parse AI responses
```

---

## 📊 AI Report Service

**File:** `backend/downloader/services/ai_report_service.py`

```python
import os
import json
import re
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from ..models import (
    VideoDownload, VideoAnalytics, AIDailyReport,
    AdSenseEarnings, AIProviderSettings
)

class AIReportService:
    """Generate AI-powered daily reports"""
    
    def __init__(self, provider=None):
        self.provider = provider or self._get_default_provider()
        self._initialize_ai_client()
    
    def _get_default_provider(self):
        """Get default AI provider from settings"""
        settings_obj = AIProviderSettings.objects.first()
        if settings_obj:
            return settings_obj.provider
        return 'gemini'
    
    def _initialize_ai_client(self):
        """Initialize AI client based on provider"""
        if self.provider == 'gemini':
            import google.generativeai as genai
            api_key = self._get_gemini_api_key()
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            self.client = None
        elif self.provider == 'openai':
            from openai import OpenAI
            self.client = OpenAI(api_key=self._get_openai_api_key())
            self.model = None
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _get_gemini_api_key(self):
        """Get Gemini API key"""
        settings_obj = AIProviderSettings.objects.first()
        if settings_obj and settings_obj.provider == 'gemini':
            return settings_obj.api_key
        return os.getenv('GEMINI_API_KEY', '')
    
    def _get_openai_api_key(self):
        """Get OpenAI API key"""
        settings_obj = AIProviderSettings.objects.first()
        if settings_obj and settings_obj.provider == 'openai':
            return settings_obj.api_key
        return os.getenv('OPENAI_API_KEY', '')
    
    # ========== MAIN REPORT GENERATION ==========
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
            
            # Shorts/Reels specific
            if video.is_short:
                report.shorts_performance = report_content.get('shorts_performance', {})
                report.viral_potential = report_content.get('viral_potential', 0)
            
            # Long video specific
            if not video.is_short:
                report.retention_analysis = report_content.get('retention_analysis', {})
            
            # Performance metrics
            report.views = analytics_data.get('views', 0)
            report.engagement_rate = analytics_data.get('engagement_rate', 0)
            report.completion_rate = analytics_data.get('completion_rate', 0)
            report.revenue_usd = analytics_data.get('revenue_usd', 0)
            
            # AI model info
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
    
    def generate_all_daily_reports(self, report_date=None):
        """Generate reports for all videos"""
        if report_date is None:
            report_date = timezone.now().date()
        
        videos = VideoDownload.objects.filter(status='success')
        reports = []
        
        for video in videos:
            try:
                report = self.generate_daily_report(video.id, report_date)
                reports.append(report)
            except Exception as e:
                print(f"Error generating report for video {video.id}: {e}")
        
        return reports
    
    # ========== DATA COLLECTION ==========
    def _collect_analytics_data(self, video, report_date):
        """Collect all analytics data for the report"""
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
        
        # Shorts/Reels specific
        completion_rate = 0
        swipe_away_rate = 0
        if video.is_short:
            completion_rates = [a.completion_rate for a in analytics if a.completion_rate > 0]
            completion_rate = sum(completion_rates) / len(completion_rates) if completion_rates else 0
            
            swipe_away_rates = [a.swipe_away_rate for a in analytics if a.swipe_away_rate > 0]
            swipe_away_rate = sum(swipe_away_rates) / len(swipe_away_rates) if swipe_away_rates else 0
        
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
            'completion_rate': completion_rate,
            'swipe_away_rate': swipe_away_rate,
            'revenue_usd': earnings,
            'video_title': video.title,
            'video_duration': video.duration,
            'is_short': video.is_short,
            'content_type': video.content_type,
            'created_at': video.created_at,
            'platforms': list(analytics.values_list('platform', flat=True).distinct()),
        }
    
    # ========== AI GENERATION ==========
    def _generate_report_with_ai(self, video, analytics_data):
        """Generate report content using AI"""
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
        
        # Parse AI response
        return self._parse_ai_response(content, analytics_data)
    
    def _build_report_prompt(self, video, analytics_data):
        """Build the prompt for AI analysis"""
        from .ai_prompt_builder import AIPromptBuilder
        builder = AIPromptBuilder()
        return builder.build_report_prompt(video, analytics_data)
    
    def _parse_ai_response(self, content, analytics_data):
        """Parse AI response into structured format"""
        from .ai_response_parser import AIResponseParser
        parser = AIResponseParser()
        return parser.parse_report_response(content, analytics_data)
```

---

## 📝 AI Prompt Builder

**File:** `backend/downloader/services/ai_prompt_builder.py`

```python
class AIPromptBuilder:
    """Build optimized prompts for AI"""
    
    def build_report_prompt(self, video, analytics_data):
        """Build report prompt optimized for content type"""
        if video.is_short:
            return self._build_shorts_prompt(video, analytics_data)
        else:
            return self._build_long_video_prompt(video, analytics_data)
    
    def _build_shorts_prompt(self, video, analytics_data):
        """Build prompt for Shorts/Reels"""
        return f"""
Analyze this Short/Reel performance data and generate a comprehensive daily report.

VIDEO INFORMATION:
- Title: {video.title}
- Type: Short/Reel ({analytics_data['video_duration']} seconds)
- Platforms: {', '.join(analytics_data['platforms'])}

PERFORMANCE METRICS:
- Total Views: {analytics_data['views']:,}
- Previous Day Views: {analytics_data['prev_views']:,}
- Views Change: {analytics_data['views_change']:+,} ({analytics_data['views_change_pct']:+.1f}%)
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
    
    def _build_long_video_prompt(self, video, analytics_data):
        """Build prompt for Long Videos"""
        return f"""
Analyze this Long Video performance data and generate a comprehensive daily report.

VIDEO INFORMATION:
- Title: {video.title}
- Type: Long Video ({analytics_data['video_duration']} seconds / {analytics_data['video_duration']/60:.1f} minutes)
- Platforms: {', '.join(analytics_data['platforms'])}

PERFORMANCE METRICS:
- Total Views: {analytics_data['views']:,}
- Previous Day Views: {analytics_data['prev_views']:,}
- Views Change: {analytics_data['views_change']:+,} ({analytics_data['views_change_pct']:+.1f}%)
- Engagement Rate: {analytics_data['engagement_rate']:.2f}%
- Watch Time: {analytics_data['watch_time_minutes']:.1f} minutes
- Revenue: ${analytics_data['revenue_usd']:.2f}

LONG VIDEO SPECIFIC ANALYSIS:
Focus on:
1. Retention analysis (when do viewers drop off?)
2. Hook effectiveness (first 15 seconds)
3. Watch time patterns
4. Thumbnail performance (CTR)
5. Optimal video length for this topic

Provide analysis in JSON format:
{{
    "summary": "2-3 sentence summary",
    "insights": [
        "Long video insight 1",
        "Long video insight 2",
        "Long video insight 3"
    ],
    "recommendations": [
        "Actionable recommendation for long videos",
        "Retention improvement suggestion",
        "Thumbnail optimization"
    ],
    "trends": {{
        "views_trend": "increasing/decreasing/stable",
        "engagement_trend": "increasing/decreasing/stable",
        "watch_time_trend": "increasing/decreasing/stable"
    }},
    "retention_analysis": {{
        "average_retention": 0-100,
        "drop_off_points": ["time when viewers left"],
        "retention_score": 0-100
    }}
}}
"""
```

---

## 🔍 AI Response Parser

**File:** `backend/downloader/services/ai_response_parser.py`

```python
import json
import re

class AIResponseParser:
    """Parse AI responses into structured format"""
    
    def parse_report_response(self, content, analytics_data):
        """Parse AI report response"""
        # Try to extract JSON from response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                return {
                    'summary': parsed.get('summary', ''),
                    'insights': parsed.get('insights', []),
                    'recommendations': parsed.get('recommendations', []),
                    'trends': parsed.get('trends', {}),
                    'shorts_performance': parsed.get('shorts_performance', {}),
                    'retention_analysis': parsed.get('retention_analysis', {}),
                    'viral_potential': parsed.get('trends', {}).get('viral_potential', 0),
                }
            except json.JSONDecodeError:
                pass
        
        # Fallback: parse manually
        return self._parse_manually(content, analytics_data)
    
    def _parse_manually(self, content, analytics_data):
        """Manual parsing fallback"""
        return {
            'summary': content[:500],
            'insights': self._extract_bullet_points(content, 'insights'),
            'recommendations': self._extract_bullet_points(content, 'recommendations'),
            'trends': {
                'views_trend': 'stable',
                'engagement_trend': 'stable',
                'growth_rate': analytics_data.get('views_change_pct', 0)
            },
            'shorts_performance': {},
            'retention_analysis': {},
            'viral_potential': 0,
        }
    
    def _extract_bullet_points(self, text, section):
        """Extract bullet points from text"""
        lines = text.split('\n')
        points = []
        for line in lines:
            if line.strip().startswith('-') or line.strip().startswith('*'):
                points.append(line.strip()[1:].strip())
        return points[:5]  # Max 5 points
```

---

## ✅ Testing

### Unit Tests

```python
# backend/downloader/tests/test_ai_report.py

class AIReportServiceTest(TestCase):
    def setUp(self):
        self.service = AIReportService(provider='gemini')
        self.video = VideoDownload.objects.create(
            title="Test Video",
            duration=45,
            is_short=True
        )
    
    def test_generate_daily_report(self):
        """Test generating daily report"""
        report = self.service.generate_daily_report(self.video.id)
        self.assertIsNotNone(report)
        self.assertEqual(report.report_status, 'completed')
        self.assertIsNotNone(report.summary)
```

---

## 📦 Archived Items

- ✅ Basic AI report structure
- ✅ Gemini integration

---

## ⏳ Pending Items

- [ ] Add GPT-4o-mini integration
- [ ] Improve prompt engineering
- [ ] Add response validation
- [ ] Implement caching for reports
- [ ] Add email delivery option
- [ ] Add report templates
- [ ] Implement A/B testing for prompts

---

## 🎯 Success Criteria

- [ ] AI reports generating successfully
- [ ] Both Gemini and GPT-4o-mini working
- [ ] Reports optimized for Shorts and Long Videos
- [ ] Error handling complete
- [ ] Unit tests passing

---

## 📚 Next Steps

After completing this module:
1. Test report generation
2. Verify AI quality
3. Move to **Module 05: ML Prediction Service**

