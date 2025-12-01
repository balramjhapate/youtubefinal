# Module 05: ML Prediction Service

## 🎯 Overview

This module uses Machine Learning models to predict video performance (views, engagement, revenue) for both **Shorts/Reels** and **Long Videos**. Uses scikit-learn for model training and prediction.

---

## 📋 Status

- **Status:** ⏳ Pending
- **Priority:** 🟡 Medium (Core Intelligence)
- **Dependencies:** Module 01 (Database), Module 03 (Analytics)
- **Estimated Time:** 6-7 days

---

## 🤖 ML Models

### Model Types
1. **Regression Models** - Predict numerical values (views, revenue)
2. **Classification Models** - Classify performance (high/medium/low)
3. **Ensemble Models** - Combine multiple models for better accuracy

### Algorithms Used
- Random Forest Regressor
- Gradient Boosting Regressor
- XGBoost (optional, for better performance)

---

## 📁 File Structure

```
backend/downloader/services/
├── ml_prediction_service.py    # Main prediction service
├── ml_model_trainer.py         # Model training
├── ml_feature_extractor.py     # Feature extraction
└── ml_models/                   # Saved model files
    ├── views_model.pkl
    ├── engagement_model.pkl
    └── revenue_model.pkl
```

---

## 🧠 ML Prediction Service

**File:** `backend/downloader/services/ml_prediction_service.py`

```python
import numpy as np
import joblib
import os
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from django.conf import settings
from ..models import VideoDownload, VideoAnalytics, MLPrediction
from .ml_feature_extractor import MLFeatureExtractor
from .ml_model_trainer import MLModelTrainer

class MLPredictionService:
    """ML service for video performance predictions"""
    
    def __init__(self):
        self.models = {}
        self.scaler = StandardScaler()
        self.model_dir = os.path.join(settings.BASE_DIR, 'ml_models')
        os.makedirs(self.model_dir, exist_ok=True)
        self.feature_extractor = MLFeatureExtractor()
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
            self.scaler = joblib.load(
                os.path.join(self.model_dir, 'scaler.pkl')
            )
        except FileNotFoundError:
            # Train models if they don't exist
            self._train_models()
    
    def _train_models(self):
        """Train ML models on historical data"""
        trainer = MLModelTrainer()
        trainer.train_all_models()
        
        # Reload models
        self._load_models()
    
    def predict_video_performance(self, video_id):
        """Predict performance for a video"""
        video = VideoDownload.objects.get(id=video_id)
        
        # Extract features
        features = self.feature_extractor.extract_features(video)
        if not features:
            return None
        
        # Scale features
        features_scaled = self.scaler.transform([features])
        
        # Make predictions
        predicted_views_7d = max(0, int(self.views_model.predict(features_scaled)[0] * 0.25))
        predicted_views_30d = max(0, int(self.views_model.predict(features_scaled)[0]))
        predicted_engagement_rate = max(0, self.engagement_model.predict(features_scaled)[0])
        predicted_revenue_30d = max(0, self.revenue_model.predict(features_scaled)[0])
        
        # Calculate confidence (based on model performance)
        confidence_score = self._calculate_confidence(features)
        
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
    
    def _calculate_confidence(self, features):
        """Calculate prediction confidence"""
        # Simple heuristic - can be improved with actual model metrics
        # More data = higher confidence
        confidence = 0.7  # Base confidence
        
        # Adjust based on feature completeness
        if all(f > 0 for f in features):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def retrain_models(self):
        """Retrain models with latest data"""
        trainer = MLModelTrainer()
        trainer.train_all_models()
        self._load_models()
```

---

## 🎓 ML Model Trainer

**File:** `backend/downloader/services/ml_model_trainer.py`

```python
import numpy as np
import joblib
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score
from django.conf import settings
from ..models import VideoDownload, VideoAnalytics, AdSenseEarnings
from .ml_feature_extractor import MLFeatureExtractor

class MLModelTrainer:
    """Train ML models on historical data"""
    
    def __init__(self):
        self.feature_extractor = MLFeatureExtractor()
        self.model_dir = os.path.join(settings.BASE_DIR, 'ml_models')
        os.makedirs(self.model_dir, exist_ok=True)
    
    def train_all_models(self):
        """Train all ML models"""
        # Collect training data
        X, y_views, y_engagement, y_revenue = self._collect_training_data()
        
        if len(X) < 10:  # Need at least 10 samples
            print("Not enough training data. Using default models.")
            self._create_default_models()
            return
        
        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Train views model
        self._train_views_model(X_scaled, y_views, scaler)
        
        # Train engagement model
        self._train_engagement_model(X_scaled, y_engagement, scaler)
        
        # Train revenue model
        self._train_revenue_model(X_scaled, y_revenue, scaler)
    
    def _collect_training_data(self):
        """Collect training data from database"""
        videos = VideoDownload.objects.filter(status='success')
        
        X = []
        y_views = []
        y_engagement = []
        y_revenue = []
        
        for video in videos:
            features = self.feature_extractor.extract_features(video)
            if features:
                X.append(features)
                
                # Get actual outcomes
                analytics = VideoAnalytics.objects.filter(video=video)
                total_views = sum(a.views for a in analytics)
                
                total_engagement = sum(
                    a.likes + a.comments + a.shares for a in analytics
                )
                engagement_rate = (total_engagement / total_views * 100) if total_views > 0 else 0
                
                earnings = AdSenseEarnings.objects.filter(video=video)
                total_revenue = sum(e.revenue_usd for e in earnings)
                
                y_views.append(total_views)
                y_engagement.append(engagement_rate)
                y_revenue.append(total_revenue)
        
        return np.array(X), np.array(y_views), np.array(y_engagement), np.array(y_revenue)
    
    def _train_views_model(self, X, y, scaler):
        """Train views prediction model"""
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        model = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5
        )
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        print(f"Views Model - MAE: {mae:.2f}, R2: {r2:.2f}")
        
        # Save
        joblib.dump(model, os.path.join(self.model_dir, 'views_model.pkl'))
        joblib.dump(scaler, os.path.join(self.model_dir, 'scaler.pkl'))
    
    def _train_engagement_model(self, X, y, scaler):
        """Train engagement rate prediction model"""
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        model = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5
        )
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        print(f"Engagement Model - MAE: {mae:.2f}, R2: {r2:.2f}")
        
        # Save
        joblib.dump(model, os.path.join(self.model_dir, 'engagement_model.pkl'))
    
    def _train_revenue_model(self, X, y, scaler):
        """Train revenue prediction model"""
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        model = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5
        )
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        print(f"Revenue Model - MAE: {mae:.2f}, R2: {r2:.2f}")
        
        # Save
        joblib.dump(model, os.path.join(self.model_dir, 'revenue_model.pkl'))
    
    def _create_default_models(self):
        """Create default models when no training data"""
        model = GradientBoostingRegressor(n_estimators=100)
        scaler = StandardScaler()
        
        # Create dummy data for fitting
        dummy_X = np.random.rand(10, 10)
        dummy_y = np.random.rand(10) * 1000
        
        scaler.fit(dummy_X)
        model.fit(scaler.transform(dummy_X), dummy_y)
        
        # Save
        joblib.dump(model, os.path.join(self.model_dir, 'views_model.pkl'))
        joblib.dump(model, os.path.join(self.model_dir, 'engagement_model.pkl'))
        joblib.dump(model, os.path.join(self.model_dir, 'revenue_model.pkl'))
        joblib.dump(scaler, os.path.join(self.model_dir, 'scaler.pkl'))
```

---

## 🔍 Feature Extractor

**File:** `backend/downloader/services/ml_feature_extractor.py`

```python
class MLFeatureExtractor:
    """Extract features for ML models"""
    
    def extract_features(self, video):
        """Extract features from video"""
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
            initial_engagement = (
                analytics.likes + analytics.comments + analytics.shares
            ) if analytics else 0
            
            # Keyword features
            keyword_count = len(video.target_keywords) if hasattr(video, 'target_keywords') else 0
            
            # Time features
            hour_posted = video.created_at.hour if video.created_at else 12
            day_of_week = video.created_at.weekday() if video.created_at else 0
            
            # Content type
            is_short = 1 if video.is_short else 0
            
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
                is_short,
            ]
        except Exception as e:
            print(f"Error extracting features: {e}")
            return None
```

---

## ✅ Testing

### Unit Tests

```python
# backend/downloader/tests/test_ml_prediction.py

class MLPredictionServiceTest(TestCase):
    def setUp(self):
        self.service = MLPredictionService()
        self.video = VideoDownload.objects.create(
            title="Test Video",
            duration=45,
            is_short=True
        )
    
    def test_predict_video_performance(self):
        """Test predicting video performance"""
        prediction = self.service.predict_video_performance(self.video.id)
        self.assertIsNotNone(prediction)
        self.assertGreater(prediction.predicted_views_30d, 0)
```

---

## 📦 Archived Items

- ✅ Basic ML model structure
- ✅ Feature extraction logic

---

## ⏳ Pending Items

- [ ] Add XGBoost for better performance
- [ ] Implement model versioning
- [ ] Add model evaluation metrics
- [ ] Implement feature importance analysis
- [ ] Add hyperparameter tuning
- [ ] Implement model A/B testing
- [ ] Add prediction confidence intervals

---

## 🎯 Success Criteria

- [ ] ML models trained and saved
- [ ] Predictions working for all video types
- [ ] Confidence scores calculated
- [ ] Model retraining working
- [ ] Unit tests passing

---

## 📚 Next Steps

After completing this module:
1. Test predictions accuracy
2. Retrain models with more data
3. Move to **Module 06: Keyword & CPM Analysis Service**

