"""
REST API URL Configuration for RedNote Downloader
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Import controller views
# Note: We use absolute imports here because api_urls.py is at the project root
# The controller module uses relative imports internally, which works when
# Django loads it as part of the project structure
from controller import api_views, script_views

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'videos', api_views.VideoDownloadViewSet, basename='video')
router.register(r'ai-settings', api_views.AISettingsViewSet, basename='ai-settings')
router.register(r'cloudinary-settings', api_views.CloudinarySettingsViewSet, basename='cloudinary-settings')
router.register(r'google-sheets-settings', api_views.GoogleSheetsSettingsViewSet, basename='google-sheets-settings')
router.register(r'watermark-settings', api_views.WatermarkSettingsViewSet, basename='watermark-settings')

# The API URLs are now determined automatically by the router
urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/stats/', api_views.dashboard_stats, name='dashboard-stats'),
    path('test/google-sheets/', api_views.test_google_sheets, name='test-google-sheets'),
    path('bulk/download/', api_views.bulk_download, name='bulk-download'),
    path('bulk/transcribe/', api_views.bulk_transcribe, name='bulk-transcribe'),
    path('bulk/process-ai/', api_views.bulk_process_ai, name='bulk-process-ai'),
    path('bulk/delete/', api_views.bulk_delete, name='bulk-delete'),
    path('script-generator/generate/', script_views.generate_script, name='script-generate'),
]
