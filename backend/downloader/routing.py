"""
WebSocket URL routing for real-time updates
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/video/(?P<video_id>\d+)/$', consumers.VideoProcessingConsumer.as_asgi()),
    re_path(r'ws/videos/$', consumers.VideoListConsumer.as_asgi()),
]

