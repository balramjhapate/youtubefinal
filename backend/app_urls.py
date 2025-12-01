from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .controller import views, xtts_views, script_views

app_name = 'downloader'

router = DefaultRouter()
router.register(r'api/xtts/voices', xtts_views.ClonedVoiceViewSet, basename='cloned_voices')

urlpatterns = [
    path('', views.index, name='index'),
    path('api/extract/', views.extract_video, name='extract'),
    path('api/ai-settings/', views.ai_settings, name='ai_settings'),

    # Script Generator
    path('api/script-generator/generate/', script_views.generate_script, name='script_generate'),

    # Voice Cloning (XTTS)
    path('api/xtts/generate/', xtts_views.XTTSGenerateView.as_view(), name='xtts_generate'),
    path('api/xtts/languages/', xtts_views.XTTSLanguagesView.as_view(), name='xtts_languages'),
    path('', include(router.urls)),
]
