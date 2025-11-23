from django.urls import path
from . import views

app_name = 'downloader'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/extract/', views.extract_video, name='extract'),
    path('api/ai-settings/', views.ai_settings, name='ai_settings'),
    path('api/generate-audio-prompt/', views.generate_audio_prompt_view, name='generate_audio_prompt'),
    path('api/voice-profiles/', views.voice_profiles_view, name='voice_profiles'),
    path('api/synthesize-audio/', views.synthesize_audio_view, name='synthesize_audio'),
]
