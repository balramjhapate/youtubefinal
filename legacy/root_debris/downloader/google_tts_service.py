"""
Google Text-to-Speech Service
Uses Google Cloud Text-to-Speech API (Gemini Pro TTS) for fast and reliable TTS generation
"""
import os
import tempfile
import logging
import json
import re
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    GOOGLE_TTS_AVAILABLE = True
except ImportError:
    GOOGLE_TTS_AVAILABLE = False
    logger.warning("Google Cloud Text-to-Speech not available. Install: pip install google-auth google-auth-httplib2 google-auth-oauthlib")


class GoogleTTSService:
    """Google Cloud Text-to-Speech service using Gemini Pro TTS API"""
    
    def __init__(self, credentials_json=None, credentials_path=None, api_key=None):
        """
        Initialize Google TTS service
        
        Args:
            credentials_json: Service account JSON credentials as string (preferred - uses same as Google Sheets)
            credentials_path: Path to Google Cloud credentials JSON file (optional, fallback)
            api_key: Google Cloud API key (optional, will use credentials if not provided)
        """
        if not GOOGLE_TTS_AVAILABLE:
            raise ImportError("Google Cloud authentication libraries not installed")
        
        self.api_key = api_key
        self.credentials_json = credentials_json
        self.credentials_path = credentials_path
        self._access_token = None
        self._credentials = None
        
        # API endpoint for Gemini Pro TTS
        self.api_endpoint = "https://texttospeech.googleapis.com/v1beta1/text:synthesize"
    
    def _get_credentials(self):
        """Get Google Cloud credentials from Google Sheets settings or provided JSON"""
        if self._credentials:
            return self._credentials
        
        try:
            # Priority 1: Use provided credentials_json (from Google Sheets settings)
            if self.credentials_json:
                try:
                    credentials_dict = json.loads(self.credentials_json)
                    self._credentials = service_account.Credentials.from_service_account_info(
                        credentials_dict,
                        scopes=['https://www.googleapis.com/auth/cloud-platform']
                    )
                    logger.info("Using credentials from Google Sheets settings")
                    return self._credentials
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in credentials: {e}")
                    raise Exception(f"Invalid credentials JSON: {e}")
            
            # Priority 2: Try to get from Google Sheets settings in database
            try:
                from .models import GoogleSheetsSettings
                sheets_settings = GoogleSheetsSettings.objects.first()
                if sheets_settings and sheets_settings.credentials_json:
                    credentials_dict = json.loads(sheets_settings.credentials_json)
                    self._credentials = service_account.Credentials.from_service_account_info(
                        credentials_dict,
                        scopes=['https://www.googleapis.com/auth/cloud-platform']
                    )
                    logger.info("Using credentials from Google Sheets settings in database")
                    return self._credentials
            except Exception as e:
                logger.warning(f"Could not load credentials from Google Sheets settings: {e}")
            
            # Priority 3: Use credentials_path if provided
            if self.credentials_path:
                if os.path.exists(self.credentials_path):
                    self._credentials = service_account.Credentials.from_service_account_file(
                        self.credentials_path,
                        scopes=['https://www.googleapis.com/auth/cloud-platform']
                    )
                    logger.info(f"Using credentials from file: {self.credentials_path}")
                    return self._credentials
                else:
                    raise Exception(f"Credentials file not found: {self.credentials_path}")
            
            # Priority 4: Try environment variable
            if hasattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS') and settings.GOOGLE_APPLICATION_CREDENTIALS:
                creds_path = settings.GOOGLE_APPLICATION_CREDENTIALS
                if os.path.exists(creds_path):
                    self._credentials = service_account.Credentials.from_service_account_file(
                        creds_path,
                        scopes=['https://www.googleapis.com/auth/cloud-platform']
                    )
                    logger.info(f"Using credentials from settings: {creds_path}")
                    return self._credentials
            
            # Priority 5: Try environment variable
            creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if creds_path and os.path.exists(creds_path):
                self._credentials = service_account.Credentials.from_service_account_file(
                    creds_path,
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                logger.info(f"Using credentials from environment: {creds_path}")
                return self._credentials
            
            # If we get here, no credentials found
            raise Exception(
                "Google Cloud credentials not found. Please:\n"
                "1. Configure Google Sheets settings with Service Account JSON (recommended - same credentials work for TTS)\n"
                "2. Or set GOOGLE_APPLICATION_CREDENTIALS environment variable\n"
                "3. Or provide credentials_path parameter"
            )
            
        except Exception as e:
            logger.error(f"Error getting credentials: {e}")
            raise
    
    def _get_access_token(self):
        """Get OAuth2 access token for API authentication"""
        if self._access_token:
            return self._access_token
        
        try:
            # Get credentials (from Google Sheets settings or other sources)
            credentials = self._get_credentials()
            
            # Refresh token if needed
            request = Request()
            if not credentials.valid:
                credentials.refresh(request)
            
            self._access_token = credentials.token
            return self._access_token
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error getting access token: {e}")
            if "credentials not found" in error_msg.lower() or "not found" in error_msg.lower():
                raise Exception(
                    "Google Cloud credentials not found. Please configure Google Sheets settings with Service Account JSON "
                    "(same credentials work for both Sheets and TTS). See Settings page."
                )
            raise
    
    def generate_speech(
        self,
        text,
        language_code='hi-IN',
        voice_name='Alnilam',
        model_name='gemini-2.5-pro-tts',
        output_path=None,
        speaking_rate=1.0,
        pitch=0.0,
        prompt=None,
        temperature=None
    ):
        """
        Generate speech using Google Gemini Pro TTS API
        
        Args:
            text: Text to synthesize
            language_code: Language code (e.g., 'hi-IN' for Hindi, 'en-US' for English)
            voice_name: Specific voice name (default: 'Alnilam' for Hindi)
            model_name: TTS model name (default: 'gemini-2.5-pro-tts')
            output_path: Path to save audio file (optional, returns bytes if not provided)
            speaking_rate: Speaking rate (0.25 to 4.0, default 1.0)
            pitch: Pitch adjustment (-20.0 to 20.0 semitones, default 0.0)
            prompt: Style/tone prompt (e.g., "Read aloud in a warm, welcoming tone.")
            temperature: Temperature for voice variation (optional)
        
        Returns:
            bytes: Audio data if output_path not provided, else None
        """
        try:
            # Build request payload matching the API format from the demo
            payload = {
                "input": {
                    "text": text
                },
                "voice": {
                    "languageCode": language_code,
                    "modelName": model_name,
                    "name": voice_name
                },
                "audioConfig": {
                    "audioEncoding": "LINEAR16",  # Can also use "MP3" if preferred
                    "pitch": pitch,
                    "speakingRate": speaking_rate
                }
            }
            
            # Add prompt if provided (for tone/style control)
            if prompt:
                payload["input"]["prompt"] = prompt
            
            # Get access token
            access_token = self._get_access_token()
            
            # Make API request
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                self.api_endpoint,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('error', {}).get('message', f"HTTP {response.status_code}")
                logger.error(f"Google TTS API error: {error_msg}")
                
                # Check if API is not enabled
                if 'has not been used' in error_msg or 'is disabled' in error_msg or 'Enable it by visiting' in error_msg:
                    # Extract project ID if available
                    project_match = re.search(r'project\s+(\d+)', error_msg)
                    project_id = project_match.group(1) if project_match else 'your-project'
                    enable_url = f"https://console.cloud.google.com/apis/api/texttospeech.googleapis.com/overview?project={project_id}"
                    raise Exception(
                        f"Google Cloud Text-to-Speech API is not enabled for your project.\n\n"
                        f"To fix this:\n"
                        f"1. Go to: {enable_url}\n"
                        f"2. Click 'Enable' to enable the Text-to-Speech API\n"
                        f"3. Wait 1-2 minutes for the API to be activated\n"
                        f"4. Try reprocessing the video again\n\n"
                        f"Note: The same service account credentials from Google Sheets settings will work once the API is enabled."
                    )
                
                raise Exception(f"Google TTS API error: {error_msg}")
            
            # Extract audio content (base64 encoded)
            result = response.json()
            audio_content_b64 = result.get('audioContent', '')
            
            if not audio_content_b64:
                raise Exception("No audio content in API response")
            
            # Decode base64 audio
            import base64
            audio_content = base64.b64decode(audio_content_b64)
            
            # Convert LINEAR16 to MP3 if needed (or save as WAV)
            if output_path:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # If output is MP3, convert LINEAR16 to MP3 using ffmpeg
                if output_path.endswith('.mp3'):
                    # Save LINEAR16 to temp file first
                    temp_wav = output_path.replace('.mp3', '.wav')
                    with open(temp_wav, 'wb') as out:
                        out.write(audio_content)
                    
                    # Convert to MP3 using ffmpeg
                    from .utils import find_ffmpeg
                    import subprocess
                    ffmpeg_path = find_ffmpeg()
                    if ffmpeg_path:
                        cmd = [
                            ffmpeg_path,
                            '-i', temp_wav,
                            '-acodec', 'libmp3lame',
                            '-y',
                            output_path
                        ]
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                        if result.returncode == 0 and os.path.exists(output_path):
                            os.remove(temp_wav)
                        else:
                            # Fallback: rename WAV to MP3 (or keep as WAV)
                            logger.warning(f"FFmpeg conversion failed, keeping WAV format")
                            if os.path.exists(temp_wav):
                                os.rename(temp_wav, output_path.replace('.mp3', '.wav'))
                    else:
                        # No ffmpeg, save as WAV
                        logger.warning(f"FFmpeg not found, saving as WAV instead of MP3")
                        if os.path.exists(temp_wav):
                            os.rename(temp_wav, output_path.replace('.mp3', '.wav'))
                else:
                    # Save directly as WAV or other format
                    with open(output_path, 'wb') as out:
                        out.write(audio_content)
                
                logger.info(f"Generated TTS audio saved to: {output_path}")
                return None
            else:
                return audio_content
                
        except Exception as e:
            logger.error(f"Google TTS generation error: {e}")
            raise
    
    def list_voices(self, language_code=None):
        """
        List available voices
        
        Args:
            language_code: Filter by language code (optional)
        
        Returns:
            list: List of available voices
        """
        try:
            if language_code:
                voices = self.client.list_voices(language_code=language_code)
            else:
                voices = self.client.list_voices()
            
            return [voice for voice in voices.voices]
        except Exception as e:
            logger.error(f"Error listing voices: {e}")
            return []


def calculate_optimal_speed(video_duration, script_text, base_speed=1.0):
    """
    Calculate optimal TTS speed to match video duration
    
    Args:
        video_duration: Video duration in seconds
        script_text: Text to be spoken
        base_speed: Base speaking rate (default 1.0)
    
    Returns:
        float: Optimal speaking rate
    """
    if not video_duration or not script_text:
        return base_speed
    
    # Estimate speech duration at base speed
    # Average speaking rate: ~150 words per minute = 2.5 words per second
    # Average word length in Hindi: ~5 characters
    words = len(script_text.split())
    estimated_duration = words / 2.5  # seconds at base speed
    
    if estimated_duration <= 0:
        return base_speed
    
    # Calculate speed adjustment needed
    # If estimated duration > video duration, need to speed up
    # If estimated duration < video duration, can slow down slightly
    speed_ratio = estimated_duration / video_duration
    
    # Clamp speed between 0.5x and 2.0x for natural speech
    optimal_speed = base_speed * speed_ratio
    optimal_speed = max(0.5, min(2.0, optimal_speed))
    
    return round(optimal_speed, 2)

