"""
WebSocket utility functions for broadcasting video processing updates
"""
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

def get_visual_analysis_provider():
    """Get visual analysis provider from settings"""
    try:
        from model import AIProviderSettings
        settings_obj = AIProviderSettings.objects.first()
        if settings_obj:
            return settings_obj.visual_analysis_provider or 'openai'
        return 'openai'
    except Exception:
        return 'openai'


def broadcast_video_update(video_id, update_data=None, video_instance=None):
    """
    Broadcast video processing update to all connected WebSocket clients
    
    Args:
        video_id: Video ID
        update_data: Optional dictionary with update information (if None, will fetch from video_instance)
        video_instance: Optional VideoDownload instance (if update_data is None, will fetch full status)
    """
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return
        
        # Get full video status if update_data not provided
        if update_data is None:
            if video_instance:
                update_data = get_video_status_data(video_instance)
            else:
                try:
                    from model import VideoDownload
                    video = VideoDownload.objects.get(pk=video_id)
                    update_data = get_video_status_data(video)
                except Exception as e:
                    print(f"[WEBSOCKET] Error fetching video {video_id}: {e}")
                    return
        
        room_group_name = f'video_{video_id}'
        
        # Send update to video-specific room
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'video_update',
                'data': update_data
            }
        )
        
        # Also send to video list room for list updates
        async_to_sync(channel_layer.group_send)(
            'video_list',
            {
                'type': 'video_list_update',
                'data': {
                    'video_id': video_id,
                    'update': update_data
                }
            }
        )
        
        print(f"[WEBSOCKET] Broadcasted update for video {video_id}")
    except Exception as e:
        # Don't fail if WebSocket is not available
        print(f"[WEBSOCKET] Error broadcasting update: {e}")


def get_video_status_data(video):
    """
    Get comprehensive video status data for WebSocket updates
    
    Args:
        video: VideoDownload model instance
        
    Returns:
        dict: Complete video status data
    """
    from django.utils import timezone
    from django.utils.dateformat import format as date_format
    
    def format_datetime(dt):
        if dt:
            return dt.isoformat()
        return None
    
    # Use getattr with safe defaults to prevent AttributeError
    try:
        return {
            'id': video.id,
            'title': getattr(video, 'title', ''),
            'video_id': getattr(video, 'video_id', None),
            'video_url': getattr(video, 'video_url', None),
            
            # Download status
            'is_downloaded': getattr(video, 'is_downloaded', False),
        'extraction_started_at': format_datetime(getattr(video, 'extraction_started_at', None)),
        'extraction_finished_at': format_datetime(getattr(video, 'extraction_finished_at', None)),
        # Legacy field names for compatibility
        'download_started_at': format_datetime(getattr(video, 'extraction_started_at', None)),
        'download_finished_at': format_datetime(getattr(video, 'extraction_finished_at', None)),
        
        # Transcription status
        'transcription_status': getattr(video, 'transcription_status', 'not_transcribed'),
        'transcript_started_at': format_datetime(getattr(video, 'transcript_started_at', None)),
        'transcript_processed_at': format_datetime(getattr(video, 'transcript_processed_at', None)),
        'transcript_error_message': getattr(video, 'transcript_error_message', ''),
        
        # Whisper transcription status
        'whisper_transcription_status': getattr(video, 'whisper_transcription_status', 'not_transcribed'),
        'whisper_transcript_started_at': format_datetime(getattr(video, 'whisper_transcript_started_at', None)),
        'whisper_transcript_finished_at': format_datetime(getattr(video, 'whisper_transcript_processed_at', None)),
        
        # Frame extraction status
        'frames_extracted': getattr(video, 'frames_extracted', False),
        'frames_extracted_at': format_datetime(getattr(video, 'frames_extracted_at', None)),
        'total_frames_extracted': getattr(video, 'total_frames_extracted', 0),
        'frames_extraction_interval': getattr(video, 'frames_extraction_interval', None),
        
        # Visual analysis status
        'visual_transcript_started_at': format_datetime(getattr(video, 'visual_transcript_started_at', None)),
        'visual_transcript_finished_at': format_datetime(getattr(video, 'visual_transcript_finished_at', None)),
        'visual_transcript': bool(getattr(video, 'visual_transcript', False)),
        # Get visual analysis provider from settings
        'visual_analysis_provider': get_visual_analysis_provider(),
        
            # Enhanced transcript status
            'ai_processing_status': getattr(video, 'ai_processing_status', 'not_processed'),
            'ai_processing_started_at': format_datetime(getattr(video, 'ai_processing_started_at', None)),
            'ai_processed_at': format_datetime(getattr(video, 'ai_processed_at', None)),
            'enhanced_transcript_started_at': format_datetime(getattr(video, 'enhanced_transcript_started_at', None)),
            'enhanced_transcript_finished_at': format_datetime(getattr(video, 'enhanced_transcript_finished_at', None)),
            'enhanced_transcript': bool(getattr(video, 'enhanced_transcript', False)),
            
            # Script generation status
            'script_status': getattr(video, 'script_status', 'not_generated'),
            'script_started_at': format_datetime(getattr(video, 'script_started_at', None)),
            'script_generated_at': format_datetime(getattr(video, 'script_generated_at', None)),
            
            # Synthesis status
            'synthesis_status': getattr(video, 'synthesis_status', 'not_synthesized'),
            'synthesis_started_at': format_datetime(getattr(video, 'synthesis_started_at', None)),
            'synthesized_at': format_datetime(getattr(video, 'synthesized_at', None)),
            
            # Final video status
            'final_video_status': getattr(video, 'final_video_status', 'not_started'),
            'final_video_started_at': format_datetime(getattr(video, 'final_video_started_at', None)),
            'final_video_finished_at': format_datetime(getattr(video, 'final_video_finished_at', None)),
            'final_processed_video_url': getattr(video, 'final_processed_video_url', None) or (getattr(video, 'final_processed_video', None) and getattr(video.final_processed_video, 'url', None) or None),
            
            # Video file URLs for Video Versions section (matching serializer field names)
            'local_file_url': getattr(video, 'local_file', None) and getattr(video.local_file, 'url', None) or None,
            'voice_removed_video_url': getattr(video, 'voice_removed_video_url', None) or (getattr(video, 'voice_removed_video', None) and getattr(video.voice_removed_video, 'url', None) or None),
            'synthesized_audio_url': getattr(video, 'synthesized_audio', None) and getattr(video.synthesized_audio, 'url', None) or None,
            'final_processed_video_file_url': getattr(video, 'final_processed_video', None) and getattr(video.final_processed_video, 'url', None) or None,
            
            # Cloudinary upload status
            'cloudinary_upload_started_at': format_datetime(getattr(video, 'cloudinary_upload_started_at', None)),
            'cloudinary_uploaded_at': format_datetime(getattr(video, 'cloudinary_uploaded_at', None)),
            'cloudinary_url': getattr(video, 'cloudinary_url', None),
            
            # Google Sheets sync status
            'google_sheets_sync_started_at': format_datetime(getattr(video, 'google_sheets_sync_started_at', None)),
            'google_sheets_synced_at': format_datetime(getattr(video, 'google_sheets_synced_at', None)),
            'google_sheets_synced': getattr(video, 'google_sheets_synced', False),
        
        # Duration and metadata
        'duration': getattr(video, 'duration', None),
        'has_audio': getattr(video, 'has_audio', True),
        
        # Timestamps
        'created_at': format_datetime(getattr(video, 'created_at', None)),
        'updated_at': format_datetime(getattr(video, 'updated_at', None)),
        }
    except Exception as e:
        print(f"[WEBSOCKET] Error in get_video_status_data for video {video.id}: {e}")
        import traceback
        traceback.print_exc()
        # Return minimal data to prevent WebSocket disconnect
        return {
            'id': video.id,
            'title': str(video),
            'error': f'Error serializing video data: {str(e)}'
        }

