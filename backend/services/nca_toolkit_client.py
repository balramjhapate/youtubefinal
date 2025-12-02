"""
NCA Toolkit API Client
Integrates with the No-Code Architects Toolkit API for fast media processing
Documentation: https://github.com/stephengpope/no-code-architects-toolkit
"""
import requests
import os
import time
import logging
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)

class NCAToolkitClient:
    """Client for interacting with NCA Toolkit API"""
    
    def __init__(self, api_url=None, api_key=None):
        """
        Initialize NCA Toolkit client
        
        Args:
            api_url: Base URL of NCA Toolkit API (defaults to settings.NCA_API_URL)
            api_key: API key for authentication (defaults to settings.NCA_API_KEY)
        """
        self.api_url = (api_url or getattr(settings, 'NCA_API_URL', 'http://localhost:8080')).rstrip('/')
        self.api_key = api_key or getattr(settings, 'NCA_API_KEY', '')
        self.timeout = getattr(settings, 'NCA_API_TIMEOUT', 600)  # 10 minutes default
        
        if not self.api_key:
            raise ValueError("NCA_API_KEY must be set in Django settings")
    
    def _make_request(self, method, endpoint, **kwargs):
        """
        Make HTTP request to NCA Toolkit API
        
        Args:
            method: HTTP method ('GET', 'POST', etc.)
            endpoint: API endpoint (e.g., '/v1/video/transcribe')
            **kwargs: Additional arguments for requests.request()
        
        Returns:
            dict: Response data or error information
        """
        url = f"{self.api_url}{endpoint}"
        headers = {
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json',
            **kwargs.pop('headers', {})
        }
        
        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                timeout=self.timeout,
                **kwargs
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'data': response.json() if response.content else {},
                    'status_code': response.status_code
                }
            else:
                error_msg = response.json().get('error', response.text) if response.content else response.text
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
        except requests.exceptions.Timeout as e:
            error_msg = f'Request timed out after {self.timeout} seconds. The API may be processing a large file or is overloaded.'
            logger.error(f"NCA Toolkit API timeout: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'error_type': 'timeout'
            }
        except requests.exceptions.ConnectionError as e:
            error_msg = f'Could not connect to NCA Toolkit API at {self.api_url}. Make sure it is running and accessible.'
            logger.error(f"NCA Toolkit API connection error: {error_msg}. Original error: {str(e)}")
            return {
                'success': False,
                'error': error_msg,
                'error_type': 'connection',
                'suggestion': 'Check if NCA Toolkit is running: docker ps | grep nca-toolkit or curl http://localhost:8080/v1/toolkit/health'
            }
        except requests.exceptions.RequestException as e:
            error_msg = f'NCA Toolkit API request failed: {str(e)}'
            logger.error(f"NCA Toolkit API request error: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'error_type': 'request'
            }
        except Exception as e:
            error_msg = f'Unexpected error calling NCA Toolkit API: {str(e)}'
            logger.error(f"NCA Toolkit API unexpected error: {error_msg}", exc_info=True)
            return {
                'success': False,
                'error': error_msg,
                'error_type': 'unknown'
            }
    
    def transcribe_video(self, video_url=None, video_file_path=None, language=None, webhook_url=None):
        """
        Transcribe video using NCA Toolkit API
        
        Args:
            video_url: URL of video to transcribe
            video_file_path: Local file path to video (will be uploaded)
            language: Language code (optional, auto-detect if not provided)
            webhook_url: Optional webhook URL for async processing
        
        Returns:
            dict: {
                'text': str (transcript),
                'language': str (detected language),
                'status': 'success' or 'failed',
                'error': str (if failed)
            }
        """
        if video_url:
            # Direct URL transcription - use /v1/media/transcribe with response_type='direct'
            # to avoid needing cloud storage configuration
            payload = {
                'media_url': video_url,
                'task': 'transcribe',
                'include_text': True,
                'include_srt': True,  # Include SRT format for timestamps
                'include_segments': True,  # Include segments with timestamps
                'response_type': 'direct'  # Direct response without cloud storage
            }
            if language:
                payload['language'] = language
            if webhook_url:
                payload['webhook_url'] = webhook_url
            
            response = self._make_request('POST', '/v1/media/transcribe', json=payload)
            
        elif video_file_path:
            # For local files, we need to upload them first or use a local server
            # For now, convert local file to a file upload format
            # Note: NCA Toolkit expects media_url, so we might need to serve the file
            # For simplicity, we'll use the URL-based approach if the file is accessible
            return {
                'text': '',
                'language': '',
                'status': 'failed',
                'error': 'Local file transcription not yet supported. Please provide a video_url.'
            }
        else:
            return {
                'text': '',
                'language': '',
                'status': 'failed',
                'error': 'Either video_url or video_file_path must be provided'
            }
        
        if response.get('success'):
            data = response.get('data', {})
            # The /v1/media/transcribe endpoint returns nested response structure:
            # { "code": 200, "response": { "text": "...", ... }, ... }
            response_data = data.get('response', {})
            if not response_data and isinstance(data, dict):
                # Fallback: check if text is directly in data
                response_data = data
            
            transcript = response_data.get('text') or response_data.get('transcript') or ''
            # Get SRT format with timestamps
            srt_text = response_data.get('srt') or response_data.get('srt_text') or ''
            # Get segments with timestamps
            segments = response_data.get('segments') or response_data.get('transcript_segments') or []
            # Language detection might be in a different field, check response structure
            detected_language = response_data.get('language') or data.get('language') or language or ''
            return {
                'text': transcript,
                'srt': srt_text,
                'segments': segments,
                'language': detected_language,
                'status': 'success',
                'error': None
            }
        else:
            return {
                'text': '',
                'language': '',
                'status': 'failed',
                'error': response.get('error', 'Unknown error')
            }
    
    def add_caption(self, video_url, transcript, caption_options=None, output_format='mp4'):
        """
        Add captions to video using NCA Toolkit API
        
        Args:
            video_url: URL of video to caption
            transcript: Transcript text or subtitle file
            caption_options: Dict with caption styling options:
                - font_family: Font family
                - font_size: Font size
                - font_color: Font color
                - background_color: Background color
                - position: Position (top, bottom, center)
                - alignment: Text alignment
            output_format: Output format (mp4, webm, etc.)
        
        Returns:
            dict: {
                'video_url': str (URL of captioned video),
                'status': 'success' or 'failed',
                'error': str (if failed)
            }
        """
        payload = {
            'video_url': video_url,
            'transcript': transcript,
            'output_format': output_format
        }
        
        if caption_options:
            payload.update(caption_options)
        
        response = self._make_request('POST', '/v1/video/caption', json=payload)
        
        if response.get('success'):
            data = response.get('data', {})
            return {
                'video_url': data.get('video_url', ''),
                'status': 'success',
                'error': None
            }
        else:
            return {
                'video_url': '',
                'status': 'failed',
                'error': response.get('error', 'Unknown error')
            }
    
    def extract_thumbnail(self, video_url, timestamp='00:00:01', output_format='jpg'):
        """
        Extract thumbnail from video using NCA Toolkit API
        
        Args:
            video_url: URL of video
            timestamp: Timestamp to extract (format: HH:MM:SS)
            output_format: Output format (jpg, png)
        
        Returns:
            dict: {
                'thumbnail_url': str (URL of thumbnail),
                'status': 'success' or 'failed',
                'error': str (if failed)
            }
        """
        payload = {
            'video_url': video_url,
            'timestamp': timestamp,
            'output_format': output_format
        }
        
        response = self._make_request('POST', '/v1/video/thumbnail', json=payload)
        
        if response.get('success'):
            data = response.get('data', {})
            return {
                'thumbnail_url': data.get('thumbnail_url', ''),
                'status': 'success',
                'error': None
            }
        else:
            return {
                'thumbnail_url': '',
                'status': 'failed',
                'error': response.get('error', 'Unknown error')
            }
    
    def trim_video(self, video_url, start_time, end_time, output_format='mp4'):
        """
        Trim video using NCA Toolkit API
        
        Args:
            video_url: URL of video
            start_time: Start time (format: HH:MM:SS)
            end_time: End time (format: HH:MM:SS)
            output_format: Output format (mp4, webm, etc.)
        
        Returns:
            dict: {
                'video_url': str (URL of trimmed video),
                'status': 'success' or 'failed',
                'error': str (if failed)
            }
        """
        payload = {
            'video_url': video_url,
            'start_time': start_time,
            'end_time': end_time,
            'output_format': output_format
        }
        
        response = self._make_request('POST', '/v1/video/trim', json=payload)
        
        if response.get('success'):
            data = response.get('data', {})
            return {
                'video_url': data.get('video_url', ''),
                'status': 'success',
                'error': None
            }
        else:
            return {
                'video_url': '',
                'status': 'failed',
                'error': response.get('error', 'Unknown error')
            }
    
    def split_video(self, video_url, segments, output_format='mp4'):
        """
        Split video into multiple segments using NCA Toolkit API
        
        Args:
            video_url: URL of video
            segments: List of dicts with 'start_time' and 'end_time' (format: HH:MM:SS)
            output_format: Output format (mp4, webm, etc.)
        
        Returns:
            dict: {
                'video_urls': list (URLs of split videos),
                'status': 'success' or 'failed',
                'error': str (if failed)
            }
        """
        payload = {
            'video_url': video_url,
            'segments': segments,
            'output_format': output_format
        }
        
        response = self._make_request('POST', '/v1/video/split', json=payload)
        
        if response.get('success'):
            data = response.get('data', {})
            return {
                'video_urls': data.get('video_urls', []),
                'status': 'success',
                'error': None
            }
        else:
            return {
                'video_urls': [],
                'status': 'failed',
                'error': response.get('error', 'Unknown error')
            }
    
    def check_status(self, job_id):
        """
        Check status of async job
        
        Args:
            job_id: Job ID returned from async operation
        
        Returns:
            dict: Job status information
        """
        response = self._make_request('GET', f'/v1/toolkit/job/status/{job_id}')
        return response
    
    def health_check(self):
        """
        Check if NCA Toolkit API is healthy
        
        Returns:
            dict: Health status
        """
        response = self._make_request('GET', '/v1/toolkit/health')
        return response
    
    def remove_audio_from_video(self, video_url, output_format='mp4'):
        """
        Remove audio track from video using NCA Toolkit API
        
        Args:
            video_url: URL of video
            output_format: Output format (mp4, webm, etc.)
        
        Returns:
            dict: {
                'video_url': str (URL of video without audio),
                'status': 'success' or 'failed',
                'error': str (if failed)
            }
        """
        payload = {
            'video_url': video_url,
            'output_format': output_format,
            'remove_audio': True
        }
        
        # Try /v1/video/process or /v1/media/process endpoint
        response = self._make_request('POST', '/v1/video/process', json=payload)
        
        if not response.get('success'):
            # Try alternative endpoint
            response = self._make_request('POST', '/v1/media/process', json=payload)
        
        if response.get('success'):
            data = response.get('data', {})
            return {
                'video_url': data.get('video_url') or data.get('output_url') or '',
                'status': 'success',
                'error': None
            }
        else:
            return {
                'video_url': '',
                'status': 'failed',
                'error': response.get('error', 'Unknown error')
            }
    
    def combine_audio_video(self, video_url, audio_url, output_format='mp4', audio_offset=0):
        """
        Combine audio track with video using NCA Toolkit API
        
        Args:
            video_url: URL of video (without audio or with audio to replace)
            audio_url: URL of audio file to add
            output_format: Output format (mp4, webm, etc.)
            audio_offset: Offset in seconds to start audio (default: 0)
        
        Returns:
            dict: {
                'video_url': str (URL of video with new audio),
                'status': 'success' or 'failed',
                'error': str (if failed)
            }
        """
        payload = {
            'video_url': video_url,
            'audio_url': audio_url,
            'output_format': output_format
        }
        
        if audio_offset > 0:
            payload['audio_offset'] = audio_offset
        
        # Try /v1/video/combine or /v1/media/combine endpoint
        response = self._make_request('POST', '/v1/video/combine', json=payload)
        
        if not response.get('success'):
            # Try alternative endpoint
            response = self._make_request('POST', '/v1/media/combine', json=payload)
        
        if response.get('success'):
            data = response.get('data', {})
            return {
                'video_url': data.get('video_url') or data.get('output_url') or '',
                'status': 'success',
                'error': None
            }
        else:
            return {
                'video_url': '',
                'status': 'failed',
                'error': response.get('error', 'Unknown error')
            }


def get_nca_client():
    """Get configured NCA Toolkit client instance"""
    try:
        # Check if NCA is enabled in database settings (NOT environment variables)
        from model import AIProviderSettings
        settings_obj = AIProviderSettings.objects.first()
        if not settings_obj or not settings_obj.enable_nca_transcription:
            return None
        
        # Check if API key is set in Django settings (can be from settings.py or environment)
        api_key = getattr(settings, 'NCA_API_KEY', '')
        if not api_key:
            print("⚠️  NCA_API_KEY not set in Django settings. NCA Toolkit will not be used.")
            print("  Please set NCA_API_KEY in settings.py or environment variables")
            return None
        
        client = NCAToolkitClient()
        
        # Test connection with health check
        try:
            health = client.health_check()
            if not health.get('success'):
                error_msg = health.get('error', 'Unknown error')
                error_type = health.get('error_type', 'unknown')
                suggestion = health.get('suggestion', '')
                logger.warning(f"NCA Toolkit health check failed: {error_msg} (type: {error_type})")
                if suggestion:
                    logger.info(f"Suggestion: {suggestion}")
                print(f"⚠️  NCA Toolkit health check failed: {error_msg}. Falling back to Whisper.")
                return None
        except Exception as e:
            logger.warning(f"NCA Toolkit connection test failed: {e}", exc_info=True)
            print(f"⚠️  NCA Toolkit connection test failed: {e}. Falling back to Whisper.")
            return None
        
        return client
    except ValueError as e:
        # API not configured, return None
        print(f"⚠️  NCA Toolkit not configured: {e}. Falling back to Whisper.")
        return None
    except Exception as e:
        print(f"⚠️  Error initializing NCA Toolkit: {e}. Falling back to Whisper.")
        return None

