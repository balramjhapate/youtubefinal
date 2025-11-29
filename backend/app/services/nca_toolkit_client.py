"""
NCA Toolkit API Client - Adapted from Django version
"""
import requests
import os
from app.config import settings


class NCAToolkitClient:
    """Client for interacting with NCA Toolkit API"""
    
    def __init__(self, api_url=None, api_key=None):
        self.api_url = (api_url or settings.NCA_API_URL).rstrip('/')
        self.api_key = api_key or settings.NCA_API_KEY
        self.timeout = settings.NCA_API_TIMEOUT
        
        if not self.api_key:
            raise ValueError("NCA_API_KEY must be set in settings")
    
    def _make_request(self, method, endpoint, **kwargs):
        """Make HTTP request to NCA Toolkit API"""
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
        """Transcribe video using NCA Toolkit API"""
        if video_url:
            payload = {
                'media_url': video_url,
                'task': 'transcribe',
                'include_text': True,
                'include_srt': False,
                'include_segments': False,
                'response_type': 'direct'
            }
            if language:
                payload['language'] = language
            if webhook_url:
                payload['webhook_url'] = webhook_url
            
            response = self._make_request('POST', '/v1/media/transcribe', json=payload)
            
            if response.get('success'):
                data = response.get('data', {})
                response_data = data.get('response', {})
                if not response_data and isinstance(data, dict):
                    response_data = data
                
                transcript = response_data.get('text') or response_data.get('transcript') or ''
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
            if not os.path.exists(video_file_path):
                return {
                    'text': '',
                    'language': '',
                    'status': 'failed',
                    'error': f'Video file not found: {video_file_path}'
                }
            
            try:
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


def get_nca_client():
    """Get configured NCA Toolkit client instance"""
    try:
        return NCAToolkitClient()
    except ValueError:
        return None

