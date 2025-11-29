"""
Gemini TTS Service
Uses Google Gemini TTS API (gemini-2.5-flash-preview-tts) for TTS generation
Based on: https://docs.cloud.google.com/text-to-speech/docs/gemini-tts
"""
import os
import tempfile
import logging
import json
import base64
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

GEMINI_TTS_AVAILABLE = True  # No special dependencies needed, just requests


class GeminiTTSService:
    """Gemini TTS service using Generative Language API"""
    
    def __init__(self, api_key=None):
        """
        Initialize Gemini TTS service
        
        Args:
            api_key: Gemini API key (will be fetched from AIProviderSettings if not provided)
        """
        self.api_key = api_key
        if not self.api_key:
            # Get API key from AIProviderSettings
            try:
                from .models import AIProviderSettings
                settings_obj = AIProviderSettings.objects.first()
                if settings_obj and settings_obj.api_key:
                    self.api_key = settings_obj.api_key
                    logger.info("Using Gemini API key from AIProviderSettings")
                else:
                    raise Exception("Gemini API key not found in AIProviderSettings")
            except Exception as e:
                logger.error(f"Error getting Gemini API key: {e}")
                raise Exception(f"Gemini API key not configured: {e}")
        
        # API endpoint for Gemini TTS
        self.api_endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent"
    
    def generate_speech(
        self,
        text,
        language_code='hi-IN',
        voice_name='Enceladus',
        output_path=None,
        temperature=None,
        style_prompt=None
    ):
        """
        Generate speech using Gemini TTS API with support for markup tags and style prompts
        
        Args:
            text: Text to synthesize (can include markup tags like [sigh], [laughing], [short pause], etc.)
            language_code: Language code (default: 'hi-IN' for Hindi)
            voice_name: Voice name (default: 'Enceladus' for Hindi)
            output_path: Output file path (if None, returns audio bytes)
            temperature: Temperature for generation (optional)
            style_prompt: Style prompt for overall tone (e.g., "You are an engaging explainer speaking in a friendly and energetic tone")
        
        Returns:
            bytes: Audio content if output_path is None, otherwise None (saves to file)
        """
        try:
            # Analyze text content to determine appropriate style
            has_fear_keywords = any(keyword in text.lower() for keyword in ['राक्षस', 'डर', 'अंधेरा', 'भय', 'साहस', 'पीछा', 'भाग', 'दौड़'])
            has_exciting_keywords = any(keyword in text.lower() for keyword in ['देखो', 'वाह', 'अरे', 'मजेदार', 'रोमांचक'])
            
            # Create detailed style prompt based on content
            if not style_prompt:
                if has_fear_keywords:
                    style_prompt = """You are narrating a suspenseful and engaging story for children. 
                    - Use a dramatic, slightly tense tone when describing scary or suspenseful moments
                    - Use [whispering] tags to create atmosphere for fear elements
                    - Use [sigh] for relief or tension
                    - Maintain energy and engagement throughout
                    - This is children's content, so keep it exciting but not too scary
                    - Respect all markup tags: [short pause], [medium pause], [long pause], [sigh], [laughing], [uhm], [whispering]
                    - Pause tags control timing: [short pause] = brief pause, [medium pause] = sentence break, [long pause] = dramatic pause
                    - Expression tags add sounds: [sigh] = sigh sound, [laughing] = laugh, [uhm] = hesitation
                    - Style tags modify delivery: [whispering] = quieter voice
                    - Read the text exactly as written, following all markup tags precisely"""
                elif has_exciting_keywords:
                    style_prompt = """You are an engaging, energetic, and detailed explainer for children's content.
                    - Speak in a friendly, vivid, and enthusiastic tone
                    - Be enthusiastic about scenes and actions
                    - Use [laughing] tags naturally for fun moments
                    - Maintain high energy and excitement
                    - Respect all markup tags: [short pause], [medium pause], [long pause], [sigh], [laughing], [uhm]
                    - Pause tags control timing: [short pause] = brief pause, [medium pause] = sentence break, [long pause] = dramatic pause
                    - Expression tags add sounds: [sigh] = sigh sound, [laughing] = laugh, [uhm] = hesitation
                    - Read the text exactly as written, following all markup tags precisely"""
                else:
                    style_prompt = """You are an engaging, energetic, and detailed explainer. 
                    - Speak in a friendly, vivid, and descriptive tone
                    - Be enthusiastic about scenes and actions
                    - This is for children's content, so make it fun and exciting
                    - Respect all markup tags: [short pause], [medium pause], [long pause], [sigh], [laughing], [uhm], [whispering]
                    - Pause tags control timing: [short pause] = brief pause (~250ms), [medium pause] = sentence break (~500ms), [long pause] = dramatic pause (~1000ms+)
                    - Expression tags add sounds: [sigh] = sigh sound, [laughing] = laugh, [uhm] = hesitation
                    - Style tags modify delivery: [whispering] = quieter voice, [shouting] = louder voice
                    - Read the text exactly as written, following all markup tags precisely"""
            
            # Prepare request payload based on n8n node structure and Gemini TTS documentation
            # The text can include markup tags like [sigh], [laughing], [short pause], [medium pause], [long pause], etc.
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": f"{style_prompt}\n\nRead the following text with all markup tags:\n\n{text}"
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {
                        "voiceConfig": {
                            "prebuiltVoiceConfig": {
                                "voiceName": voice_name
                            }
                        }
                    }
                }
            }
            
            # Add temperature if provided
            if temperature is not None:
                payload["generationConfig"]["temperature"] = temperature
            
            # Make API request
            headers = {
                "Content-Type": "application/json"
            }
            
            # Use API key in query parameter (Gemini API standard)
            url = f"{self.api_endpoint}?key={self.api_key}"
            
            logger.info(f"Generating TTS with Gemini TTS (voice: {voice_name}, language: {language_code})...")
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=120  # 2 minutes timeout for TTS generation
            )
            
            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('error', {}).get('message', f"HTTP {response.status_code}")
                logger.error(f"Gemini TTS API error: {error_msg}")
                raise Exception(f"Gemini TTS API error: {error_msg}")
            
            # Parse response
            result = response.json()
            
            # Extract audio content from response
            # Based on Gemini TTS API documentation, audio is returned in candidates[0].content.parts[0].inlineData
            audio_content_b64 = None
            
            # Check for audio in candidates (standard Gemini API response)
            if 'candidates' in result and len(result['candidates']) > 0:
                candidate = result['candidates'][0]
                if 'content' in candidate:
                    parts = candidate['content'].get('parts', [])
                    for part in parts:
                        # Check for inlineData with audio/pcm mimeType
                        if 'inlineData' in part:
                            inline_data = part['inlineData']
                            mime_type = inline_data.get('mimeType', '')
                            if 'audio' in mime_type.lower() or 'pcm' in mime_type.lower():
                                audio_content_b64 = inline_data.get('data')
                                logger.info(f"Found audio in inlineData with mimeType: {mime_type}")
                                break
                        # Check if text field contains base64 audio (fallback)
                        elif 'text' in part and part.get('text'):
                            text_data = part['text']
                            # Try to decode if it looks like base64
                            try:
                                decoded = base64.b64decode(text_data)
                                if len(decoded) > 1000:  # Likely audio data
                                    audio_content_b64 = text_data
                                    logger.info("Found audio in text field (base64)")
                                    break
                            except:
                                pass
            
            # Alternative: Check for audioContent directly (some API versions)
            if not audio_content_b64 and 'audioContent' in result:
                audio_content_b64 = result['audioContent']
                logger.info("Found audio in audioContent field")
            
            if not audio_content_b64:
                # Try to find any base64 audio data in the response
                response_str = json.dumps(result)
                # Look for base64 patterns
                import re
                base64_pattern = r'"data"\s*:\s*"([A-Za-z0-9+/=]{100,})"'
                matches = re.findall(base64_pattern, response_str)
                if matches:
                    audio_content_b64 = matches[0]
                    logger.info("Found audio using regex pattern matching")
            
            if not audio_content_b64:
                logger.error(f"Response structure: {json.dumps(result, indent=2)[:1000]}")
                raise Exception("No audio content found in API response. Check logs for response structure.")
            
            # Decode base64 audio
            audio_content = base64.b64decode(audio_content_b64)
            
            # Convert PCM to MP3 if needed
            if output_path and output_path.endswith('.mp3'):
                # Save PCM to temp file first
                temp_pcm = tempfile.NamedTemporaryFile(delete=False, suffix='.pcm')
                temp_pcm_path = temp_pcm.name
                temp_pcm.write(audio_content)
                temp_pcm.close()
                
                # Convert PCM to MP3 using ffmpeg
                from .utils import find_ffmpeg
                import subprocess
                
                ffmpeg_path = find_ffmpeg()
                if not ffmpeg_path:
                    # If ffmpeg not available, save as WAV instead
                    logger.warning("ffmpeg not found, saving as WAV instead of MP3")
                    output_path = output_path.replace('.mp3', '.wav')
                    with open(output_path, 'wb') as f:
                        # Write WAV header + PCM data
                        # Simple WAV header for 16-bit PCM, 24kHz (common for TTS)
                        sample_rate = 24000
                        channels = 1
                        bits_per_sample = 16
                        data_size = len(audio_content)
                        file_size = 36 + data_size
                        
                        wav_header = b'RIFF'
                        wav_header += file_size.to_bytes(4, 'little')
                        wav_header += b'WAVE'
                        wav_header += b'fmt '
                        wav_header += (16).to_bytes(4, 'little')  # fmt chunk size
                        wav_header += (1).to_bytes(2, 'little')  # audio format (PCM)
                        wav_header += channels.to_bytes(2, 'little')
                        wav_header += sample_rate.to_bytes(4, 'little')
                        wav_header += (sample_rate * channels * bits_per_sample // 8).to_bytes(4, 'little')
                        wav_header += (channels * bits_per_sample // 8).to_bytes(2, 'little')
                        wav_header += bits_per_sample.to_bytes(2, 'little')
                        wav_header += b'data'
                        wav_header += data_size.to_bytes(4, 'little')
                        
                        f.write(wav_header)
                        f.write(audio_content)
                    
                    os.unlink(temp_pcm_path)
                    logger.info(f"Generated TTS audio saved to: {output_path}")
                    return None
                else:
                    # Convert PCM to MP3 using ffmpeg
                    cmd = [
                        ffmpeg_path,
                        '-f', 's16le',  # 16-bit signed little-endian PCM
                        '-ar', '24000',  # Sample rate (common for TTS)
                        '-ac', '1',  # Mono
                        '-i', temp_pcm_path,
                        '-acodec', 'libmp3lame',
                        '-b:a', '192k',
                        '-y',
                        output_path
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    os.unlink(temp_pcm_path)
                    
                    if result.returncode == 0 and os.path.exists(output_path):
                        logger.info(f"Generated TTS audio saved to: {output_path}")
                        return None
                    else:
                        error_msg = f"ffmpeg conversion failed: {result.stderr[:500] if result.stderr else 'Unknown error'}"
                        logger.error(error_msg)
                        raise Exception(error_msg)
            else:
                # Save directly (WAV or other format)
                if output_path:
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    with open(output_path, 'wb') as f:
                        f.write(audio_content)
                    logger.info(f"Generated TTS audio saved to: {output_path}")
                    return None
                else:
                    return audio_content
                    
        except Exception as e:
            logger.error(f"Gemini TTS generation error: {e}", exc_info=True)
            raise

