from django.urls import path
from . import views

app_name = 'downloader'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/extract/', views.extract_video, name='extract'),
    path('api/ai-settings/', views.ai_settings, name='ai_settings'),
]
