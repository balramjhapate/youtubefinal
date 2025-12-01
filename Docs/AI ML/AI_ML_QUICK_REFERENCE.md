# AI & ML Analytics - Quick Reference

## 🎯 What You're Getting

### 1. **AI Daily Reports** (Every Evening at 6 PM)
- ✅ Automatic analysis of each video's performance
- ✅ Insights, recommendations, and trends
- ✅ Uses GPT-4o-mini or Gemini
- ✅ Emailed or displayed in dashboard

### 2. **ML Predictions**
- ✅ Predicted views (7 days, 30 days)
- ✅ Predicted engagement rate
- ✅ Predicted revenue
- ✅ Confidence scores

### 3. **Keyword & CPM Analysis**
- ✅ High CPM keyword detection
- ✅ Competition analysis
- ✅ SEO score and suggestions
- ✅ Keyword performance tracking

### 4. **AdSense Earnings**
- ✅ Daily revenue tracking
- ✅ CPM, RPM, CTR metrics
- ✅ Earnings per video
- ✅ Geographic breakdown

---

## 📋 Quick Setup

### Step 1: Install Packages
```bash
pip install google-generativeai openai scikit-learn joblib numpy pandas celery redis
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### Step 2: Add Models to Database
```bash
# Add new models to backend/downloader/models.py
# Run migrations
python manage.py makemigrations
python manage.py migrate
```

### Step 3: Configure Celery
```bash
# Install Redis
brew install redis  # macOS
# or
sudo apt-get install redis-server  # Linux

# Start Redis
redis-server

# Start Celery worker
celery -A rednote_project worker --loglevel=info

# Start Celery beat (scheduler)
celery -A rednote_project beat --loglevel=info
```

### Step 4: Set Environment Variables
```bash
# .env file
GEMINI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key
ADSENSE_CLIENT_ID=your_adsense_client_id
ADSENSE_CLIENT_SECRET=your_adsense_secret
```

---

## 🕐 Scheduled Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| **AI Daily Reports** | 6:00 PM Daily | Generate reports for all videos |
| **AdSense Sync** | 9:00 AM Daily | Sync earnings data |
| **ML Predictions** | 12:00 AM Daily | Update predictions |
| **Keyword Analysis** | 2:00 AM Daily | Analyze keywords |

---

## 📊 Example AI Report

```
📊 Daily Report - "How to Make Money Online"
Date: 2024-01-15

SUMMARY:
Your video gained 1,234 new views today (+15% from yesterday), 
with strong engagement at 4.2%. Revenue increased to $12.45.

KEY INSIGHTS:
• Views are trending upward - 3rd consecutive day of growth
• Engagement rate is above your channel average (3.8%)
• Watch time improved by 8% - viewers watching longer
• Revenue per view increased - better CPM keywords working

RECOMMENDATIONS:
1. Create similar content - this topic resonates with your audience
2. Post at 3 PM tomorrow - your audience is most active then
3. Add more high CPM keywords: "passive income", "online business"
4. Consider creating a series - viewers want more on this topic

TRENDS:
• Views: ↗️ Increasing (15% growth)
• Engagement: ↗️ Increasing (4.2% → 4.5%)
• Revenue: ↗️ Increasing ($10.20 → $12.45)
• Growth Rate: +15.3%
```

---

## 🧠 ML Predictions Example

```json
{
  "predicted_views_7d": 8,500,
  "predicted_views_30d": 35,000,
  "predicted_engagement_rate": 4.2,
  "predicted_revenue_30d": 125.50,
  "confidence_score": 0.78,
  "features_used": {
    "duration": 300,
    "title_length": 45,
    "has_transcript": true,
    "keyword_count": 8
  }
}
```

---

## 🔍 Keyword Analysis Example

```json
{
  "primary_keywords": [
    "make money online",
    "passive income",
    "online business"
  ],
  "high_cpm_keywords": [
    {
      "keyword": "passive income",
      "cpm": 8.50,
      "competition": "medium"
    },
    {
      "keyword": "online business",
      "cpm": 7.20,
      "competition": "high"
    }
  ],
  "competition_level": "medium",
  "seo_score": 75,
  "seo_suggestions": [
    {
      "type": "keyword",
      "message": "Add high CPM keyword 'passive income' to title",
      "priority": "high"
    }
  ]
}
```

---

## 💰 AdSense Earnings Example

```json
{
  "earnings": [
    {
      "date": "2024-01-15",
      "revenue_usd": 12.45,
      "impressions": 5,234,
      "clicks": 45,
      "cpm": 2.38,
      "rpm": 2.50
    }
  ],
  "total_revenue": 125.50,
  "average_cpm": 2.35,
  "period_days": 30
}
```

---

## 🎯 API Endpoints

### Get AI Report
```http
GET /api/videos/{video_id}/ai-report/?date=2024-01-15
```

### Get ML Predictions
```http
GET /api/videos/{video_id}/ml-predictions/
```

### Get Keyword Analysis
```http
GET /api/videos/{video_id}/keyword-analysis/
```

### Get AdSense Earnings
```http
GET /api/videos/{video_id}/adsense-earnings/?days=30
```

### Generate Report Now
```http
POST /api/videos/{video_id}/generate-report/
```

---

## 🚀 Quick Start Commands

### Generate Report for One Video
```python
from downloader.services.ai_report_service import AIReportService

service = AIReportService(provider='gemini')
report = service.generate_daily_report(video_id=1)
print(report.summary)
```

### Get ML Predictions
```python
from downloader.services.ml_prediction_service import MLPredictionService

service = MLPredictionService()
prediction = service.predict_video_performance(video_id=1)
print(f"Predicted views: {prediction.predicted_views_30d}")
```

### Analyze Keywords
```python
from downloader.services.keyword_service import KeywordAnalysisService

service = KeywordAnalysisService()
analysis = service.analyze_video_keywords(video_id=1)
print(analysis.high_cpm_keywords)
```

---

## 📧 Email Reports (Optional)

You can configure email delivery:

```python
# In ai_report_service.py
def send_report_email(report):
    from django.core.mail import send_mail
    
    subject = f"Daily Report: {report.video.title}"
    message = f"""
    {report.summary}
    
    Insights:
    {chr(10).join(report.insights)}
    
    Recommendations:
    {chr(10).join(report.recommendations)}
    """
    
    send_mail(
        subject=subject,
        message=message,
        from_email='reports@yourdomain.com',
        recipient_list=['you@email.com'],
    )
```

---

## 🎨 Frontend Integration

### Display AI Report Component
```jsx
import { useQuery } from '@tanstack/react-query';
import { videosApi } from '../api';

function AIReportPanel({ videoId }) {
  const { data: report } = useQuery({
    queryKey: ['ai-report', videoId],
    queryFn: () => videosApi.getAIReport(videoId),
  });
  
  return (
    <div>
      <h3>Daily AI Report</h3>
      <p>{report?.summary}</p>
      <ul>
        {report?.insights.map((insight, i) => (
          <li key={i}>{insight}</li>
        ))}
      </ul>
    </div>
  );
}
```

---

## ✅ Checklist

- [ ] Install packages
- [ ] Add database models
- [ ] Run migrations
- [ ] Set up Celery
- [ ] Configure API keys
- [ ] Test AI report generation
- [ ] Test ML predictions
- [ ] Test keyword analysis
- [ ] Set up AdSense integration
- [ ] Create frontend components
- [ ] Schedule daily tasks

---

## 🎉 Result

You'll have:
- ✅ AI-powered insights every evening
- ✅ ML predictions for all videos
- ✅ Keyword optimization suggestions
- ✅ AdSense earnings tracking
- ✅ Automated daily reports
- ✅ Data-driven content strategy

**Your dashboard becomes an intelligent analytics platform!** 🚀

