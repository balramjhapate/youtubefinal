from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .controller import views, script_views

app_name = 'downloader'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/extract/', views.extract_video, name='extract'),
    path('api/ai-settings/', views.ai_settings, name='ai_settings'),

    # Script Generator
    path('api/script-generator/generate/', script_views.generate_script, name='script_generate'),
]
