"""
REST API URL Configuration for RedNote Downloader
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views, xtts_views

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'videos', api_views.VideoDownloadViewSet, basename='video')
router.register(r'settings', api_views.AISettingsViewSet, basename='settings')

# The API URLs are now determined automatically by the router
urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/stats/', api_views.dashboard_stats, name='dashboard-stats'),
    path('bulk/download/', api_views.bulk_download, name='bulk-download'),
    path('bulk/transcribe/', api_views.bulk_transcribe, name='bulk-transcribe'),
    path('bulk/process-ai/', api_views.bulk_process_ai, name='bulk-process-ai'),
    path('bulk/delete/', api_views.bulk_delete, name='bulk-delete'),
    path('xtts/generate/', xtts_views.XTTSGenerateView.as_view(), name='xtts-generate'),
    path('xtts/languages/', xtts_views.XTTSLanguagesView.as_view(), name='xtts-languages'),
]
