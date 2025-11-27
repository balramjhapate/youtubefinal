from django.urls import path
from . import views, xtts_views, bulk_views

app_name = 'downloader'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/videos/extract/', views.extract_video, name='extract_video'),
    path('api/videos/', views.list_videos, name='list_videos'),
    path('api/videos/<int:video_id>/download/', views.download_video, name='download_video'),
    path('api/videos/<int:video_id>/transcribe/', views.transcribe_video_view, name='transcribe_video'),
    path('api/videos/<int:video_id>/transcription_status/', views.get_transcription_status, name='get_transcription_status'),
    path('api/videos/<int:video_id>/process_ai/', views.process_ai_view, name='process_ai'),
    path('api/videos/<int:video_id>/generate_audio_prompt/', views.generate_audio_prompt_view, name='generate_audio_prompt'),
    path('api/videos/<int:video_id>/synthesize/', views.synthesize_audio_view, name='synthesize_audio'),
    path('api/videos/<int:video_id>/update_voice_profile/', views.update_voice_profile_view, name='update_voice_profile'),
    path('api/videos/<int:video_id>/', views.get_video, name='get_video'),  # GET for detail  
    path('api/videos/<int:video_id>/delete/', views.delete_video, name='delete_video'),  # DELETE moved to /delete/
    path('api/ai-settings/', views.ai_settings, name='ai_settings'),
    
    # Bulk operations
    path('api/bulk/delete/', bulk_views.bulk_delete_videos, name='bulk_delete'),
    
    # XTTS Endpoints
    path('api/xtts/languages/', xtts_views.get_languages, name='xtts_languages'),
    path('api/xtts/voices/', xtts_views.manage_voices, name='xtts_voices'),
    path('api/xtts/voices/<int:voice_id>/', xtts_views.delete_voice, name='xtts_delete_voice'),
    path('api/xtts/generate/', xtts_views.generate_speech, name='xtts_generate'),
]
