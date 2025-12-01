# Module 06: Keyword & CPM Analysis Service

## 🎯 Overview

This module analyzes keywords, identifies high CPM keywords, performs competition analysis, and provides SEO optimization suggestions for both **Shorts/Reels** and **Long Videos**.

---

## 📋 Status

- **Status:** ⏳ Pending
- **Priority:** 🟡 Medium (Optimization)
- **Dependencies:** Module 01 (Database)
- **Estimated Time:** 4-5 days

---

## 🔍 Features

1. **Keyword Extraction** - From title, description, tags
2. **CPM Analysis** - Identify high CPM keywords
3. **Competition Analysis** - Analyze keyword competition
4. **SEO Scoring** - Calculate SEO score (0-100)
5. **Optimization Suggestions** - Actionable recommendations

---

## 📁 File Structure

```
backend/downloader/services/
├── keyword_analysis_service.py  # Main service
├── keyword_extractor.py          # Extract keywords
└── cpm_research_service.py      # CPM data research
```

---

## 🔑 Keyword Analysis Service

**File:** `backend/downloader/services/keyword_analysis_service.py`

```python
from ..models import VideoDownload, KeywordAnalysis
from .keyword_extractor import KeywordExtractor
from .cpm_research_service import CPMResearchService

class KeywordAnalysisService:
    """Service for keyword research and CPM analysis"""
    
    def __init__(self):
        self.keyword_extractor = KeywordExtractor()
        self.cpm_service = CPMResearchService()
    
    def analyze_video_keywords(self, video_id):
        """Analyze keywords for a video"""
        video = VideoDownload.objects.get(id=video_id)
        
        # Extract keywords
        keywords = self.keyword_extractor.extract_keywords(video)
        
        # Get CPM data for keywords
        keyword_cpm_map = {}
        high_cpm_keywords = []
        
        for keyword in keywords:
            cpm_data = self.cpm_service.get_keyword_cpm(keyword)
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
                'primary_keywords': keywords[:10],
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
    
    def _analyze_competition(self, keywords):
        """Analyze competition level"""
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

## 📦 Archived Items

- ✅ Basic keyword extraction
- ✅ SEO scoring logic

---

## ⏳ Pending Items

- [ ] Integrate with Google Keyword Planner API
- [ ] Add SEMrush/Ahrefs integration
- [ ] Implement keyword trend analysis
- [ ] Add keyword performance tracking
- [ ] Implement keyword A/B testing

---

## 🎯 Success Criteria

- [ ] Keywords extracted correctly
- [ ] High CPM keywords identified
- [ ] SEO score calculated
- [ ] Suggestions generated
- [ ] Unit tests passing

---

## 📚 Next Steps

After completing this module:
1. Test keyword analysis
2. Verify CPM data accuracy
3. Move to **Module 07: AdSense Earnings Integration**

