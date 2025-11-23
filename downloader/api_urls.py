"""
REST API URL Configuration for RedNote Downloader
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'videos', api_views.VideoDownloadViewSet, basename='video')
router.register(r'voice-profiles', api_views.VoiceProfileViewSet, basename='voice-profile')

urlpatterns = [
    # ViewSet routes
    path('', include(router.urls)),

    # AI Settings (custom endpoints)
    path('ai-settings/', api_views.AISettingsViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='ai-settings'),

    # Dashboard stats
    path('dashboard/stats/', api_views.dashboard_stats, name='dashboard-stats'),

    # Bulk actions
    path('bulk/download/', api_views.bulk_download, name='bulk-download'),
    path('bulk/transcribe/', api_views.bulk_transcribe, name='bulk-transcribe'),
    path('bulk/process-ai/', api_views.bulk_process_ai, name='bulk-process-ai'),
    path('bulk/generate-prompts/', api_views.bulk_generate_prompts, name='bulk-generate-prompts'),
]
