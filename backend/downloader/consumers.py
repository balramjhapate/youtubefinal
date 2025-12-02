"""
WebSocket consumers for real-time video processing updates
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from model import VideoDownload
from .websocket_utils import get_video_status_data


class VideoProcessingConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for individual video processing updates"""
    
    async def connect(self):
        self.video_id = self.scope['url_route']['kwargs']['video_id']
        self.room_group_name = f'video_{self.video_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send current video status on connect
        try:
            video_data = await self.get_video_data()
            if video_data:
                await self.send(text_data=json.dumps({
                    'type': 'video_update',
                    'data': video_data,
                    'timestamp': self.get_timestamp()
                }))
        except Exception as e:
            print(f"[WEBSOCKET] Error sending initial video data: {e}")
            import traceback
            traceback.print_exc()
            # Don't close connection, just log the error
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'get_status':
                # Send current video status
                video_data = await self.get_video_data()
                if video_data:
                    await self.send(text_data=json.dumps({
                        'type': 'video_update',
                        'data': video_data,
                        'timestamp': self.get_timestamp()
                    }))
            elif message_type == 'ping':
                # Respond to ping with pong
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': self.get_timestamp()
                }))
        except json.JSONDecodeError as e:
            print(f"[WEBSOCKET] JSON decode error: {e}")
        except Exception as e:
            print(f"[WEBSOCKET] Error in receive: {e}")
            import traceback
            traceback.print_exc()
    
    async def video_update(self, event):
        """Send video update to WebSocket"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'video_update',
                'data': event['data'],
                'timestamp': self.get_timestamp()
            }))
        except Exception as e:
            print(f"[WEBSOCKET] Error sending video_update: {e}")
            import traceback
            traceback.print_exc()
    
    def get_timestamp(self):
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    @database_sync_to_async
    def get_video_data(self):
        """Get current video data from database"""
        try:
            video = VideoDownload.objects.get(pk=self.video_id)
            return get_video_status_data(video)
        except VideoDownload.DoesNotExist:
            print(f"[WEBSOCKET] Video {self.video_id} not found")
            return None
        except Exception as e:
            print(f"[WEBSOCKET] Error getting video data for {self.video_id}: {e}")
            import traceback
            traceback.print_exc()
            return None


class VideoListConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for video list updates"""
    
    async def connect(self):
        self.room_group_name = 'video_list'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def video_list_update(self, event):
        """Send video list update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'video_list_update',
            'data': event['data']
        }))

