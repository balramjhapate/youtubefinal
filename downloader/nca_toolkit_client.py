"""
NCA Toolkit API Client
Integrates with the No-Code Architects Toolkit API for fast media processing
Documentation: https://github.com/stephengpope/no-code-architects-toolkit
"""
import requests
import os
import time
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

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
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'Request timed out. The API may be processing a large file.'
            }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'error': f'Could not connect to NCA Toolkit API at {self.api_url}. Make sure it is running.'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
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
            # Direct URL transcription
            payload = {
                'video_url': video_url
            }
            if language:
                payload['language'] = language
            if webhook_url:
                payload['webhook_url'] = webhook_url
            
            response = self._make_request('POST', '/v1/video/transcribe', json=payload)
            
        elif video_file_path:
            # Upload file for transcription
            with open(video_file_path, 'rb') as video_file:
                files = {'video_file': video_file}
                data = {}
                if language:
                    data['language'] = language
                if webhook_url:
                    data['webhook_url'] = webhook_url
                
                url = f"{self.api_url}/v1/video/transcribe"
                headers = {'X-API-Key': self.api_key}
                
                try:
                    response_obj = requests.post(
                        url,
                        headers=headers,
                        files=files,
                        data=data,
                        timeout=self.timeout
                    )
                    
                    if response_obj.status_code == 200:
                        response = {
                            'success': True,
                            'data': response_obj.json(),
                            'status_code': response_obj.status_code
                        }
                    else:
                        error_msg = response_obj.json().get('error', response_obj.text) if response_obj.content else response_obj.text
                        response = {
                            'success': False,
                            'error': error_msg,
                            'status_code': response_obj.status_code
                        }
                except Exception as e:
                    response = {
                        'success': False,
                        'error': str(e)
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
            # Handle different response formats (transcript or text field)
            transcript = data.get('transcript') or data.get('text') or ''
            language = data.get('language') or data.get('lang') or ''
            return {
                'text': transcript,
                'language': language,
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


def get_nca_client():
    """Get configured NCA Toolkit client instance"""
    try:
        return NCAToolkitClient()
    except ValueError:
        # API not configured, return None
        return None

