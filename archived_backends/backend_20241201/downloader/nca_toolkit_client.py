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
            # Direct URL transcription - use /v1/media/transcribe with response_type='direct'
            # to avoid needing cloud storage configuration
            payload = {
                'media_url': video_url,
                'task': 'transcribe',
                'include_text': True,
                'include_srt': False,
                'include_segments': False,
                'response_type': 'direct'  # Direct response without cloud storage
            }
            if language:
                payload['language'] = language
            if webhook_url:
                payload['webhook_url'] = webhook_url
            
            response = self._make_request('POST', '/v1/media/transcribe', json=payload)
            
            if response.get('success'):
                data = response.get('data', {})
                # The /v1/media/transcribe endpoint returns nested response structure:
                # { "code": 200, "response": { "text": "...", ... }, ... }
                response_data = data.get('response', {})
                if not response_data and isinstance(data, dict):
                    # Fallback: check if text is directly in data
                    response_data = data
                
                transcript = response_data.get('text') or response_data.get('transcript') or ''
                # Language detection might be in a different field, check response structure
                detected_language = response_data.get('language') or data.get('language') or language or ''
                return {
                    'text': transcript,
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
            
        elif video_file_path:
            # For local files, upload them using multipart/form-data
            if not os.path.exists(video_file_path):
                return {
                    'text': '',
                    'language': '',
                    'status': 'failed',
                    'error': f'Video file not found: {video_file_path}'
                }
            
            try:
                # Upload file using multipart/form-data
                url = f"{self.api_url}/v1/media/transcribe"
                headers = {
                    'X-API-Key': self.api_key,
                }
                
                with open(video_file_path, 'rb') as video_file:
                    files = {
                        'file': (os.path.basename(video_file_path), video_file, 'video/mp4')
                    }
                    data = {
                        'task': 'transcribe',
                        'include_text': 'true',
                        'include_srt': 'false',
                        'include_segments': 'false',
                        'response_type': 'direct'
                    }
                    if language:
                        data['language'] = language
                    if webhook_url:
                        data['webhook_url'] = webhook_url
                    
                    response = requests.post(
                        url,
                        headers=headers,
                        files=files,
                        data=data,
                        timeout=self.timeout
                    )
                
                if response.status_code == 200:
                    response_data = response.json()
                    # Handle nested response structure
                    data = response_data.get('data', response_data)
                    response_data_inner = data.get('response', data)
                    
                    transcript = response_data_inner.get('text') or response_data_inner.get('transcript') or ''
                    detected_language = response_data_inner.get('language') or data.get('language') or language or ''
                    
                    return {
                        'text': transcript,
                        'language': detected_language,
                        'status': 'success',
                        'error': None
                    }
                else:
                    error_msg = response.json().get('error', response.text) if response.content else response.text
                    return {
                        'text': '',
                        'language': '',
                        'status': 'failed',
                        'error': f'API request failed: {error_msg}'
                    }
            except requests.exceptions.Timeout:
                return {
                    'text': '',
                    'language': '',
                    'status': 'failed',
                    'error': 'Request timed out. The video file may be too large.'
                }
            except requests.exceptions.ConnectionError:
                return {
                    'text': '',
                    'language': '',
                    'status': 'failed',
                    'error': f'Could not connect to NCA Toolkit API at {self.api_url}. Make sure it is running.'
                }
            except Exception as e:
                return {
                    'text': '',
                    'language': '',
                    'status': 'failed',
                    'error': f'File upload error: {str(e)}'
                }
        else:
            return {
                'text': '',
                'language': '',
                'status': 'failed',
                'error': 'Either video_url or video_file_path must be provided'
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

