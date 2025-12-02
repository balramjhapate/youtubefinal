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
import time
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
                from model import AIProviderSettings
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
        style_prompt=None,
        video_duration=None
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
            video_duration: Target duration in seconds (optional). If provided, attempts to adjust speaking rate.
        
        Returns:
            bytes: Audio content if output_path is None, otherwise None (saves to file)
        """
        try:
            # Calculate target speed if video_duration is provided
            speed_instruction = ""
            if video_duration and video_duration > 0:
                # Estimate word count (Hindi words are often longer, but space-separated count is a good proxy)
                word_count = len(text.split())
                # Average speaking rate is ~2.5 words per second (150 wpm)
                estimated_duration = word_count / 2.5
                
                # Calculate required speed factor
                # If estimated 60s but video is 30s -> need 2x speed (too fast)
                # If estimated 30s but video is 60s -> need 0.5x speed (too slow)
                speed_factor = estimated_duration / video_duration
                
                logger.info(f"TTS Speed Calculation: Words={word_count}, Video Duration={video_duration}s, Est. Audio Duration={estimated_duration:.1f}s, Factor={speed_factor:.2f}")
                
                if speed_factor > 1.3:
                    speed_instruction = "Speak at a very fast pace to fit the content in a short time."
                elif speed_factor > 1.1:
                    speed_instruction = "Speak at a slightly faster pace than normal."
                elif speed_factor < 0.7:
                    speed_instruction = "Speak at a very slow, relaxed, and deliberate pace."
                elif speed_factor < 0.9:
                    speed_instruction = "Speak at a slightly slower, more relaxed pace."
                else:
                    speed_instruction = "Speak at a natural, moderate pace."

            # Generate comprehensive style prompt using AI best practices
            if not style_prompt:
                style_prompt = self._generate_comprehensive_style_prompt(text, speed_instruction)
            else:
                # Enhance provided style prompt with speed instruction and markup guidance
                style_prompt = self._enhance_style_prompt(style_prompt, speed_instruction)
    

            
            # Prepare request payload based on n8n node structure and Gemini TTS documentation
            # The text can include markup tags like [sigh], [laughing], [short pause], [medium pause], [long pause], etc.
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": f"""{style_prompt}

**READ THIS TEXT EXACTLY AS WRITTEN:**
- Follow ALL markup tags precisely as documented above.
- **PAUSE TAGS (MODE 4) - CRITICAL:** When you see [short pause], STOP SPEAKING for ~250ms (0.25 seconds) of complete silence. When you see [medium pause], STOP SPEAKING for ~500ms (0.5 seconds) of complete silence. When you see [long pause], STOP SPEAKING for ~1000ms+ (1+ seconds) of complete silence.
- **DO NOT SPEAK THROUGH PAUSE TAGS. They insert silence into the audio - you must stop speaking completely.**

Now read this text with ALL markup tags followed precisely:

{text}"""
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
            logger.info(f"Text length: {len(text)} characters, estimated duration: {video_duration}s")
            
            # Increase timeout for longer videos/scripts
            # Base timeout: 60 seconds, add 2 seconds per second of video duration
            base_timeout = 60
            duration_timeout = int(video_duration * 2) if video_duration else 0
            total_timeout = min(base_timeout + duration_timeout, 600)  # Max 10 minutes
            
            logger.info(f"Using timeout: {total_timeout} seconds for TTS generation")
            
            # Retry logic for transient network errors
            max_retries = 2
            retry_delay = 2  # seconds
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    response = requests.post(
                        url,
                        headers=headers,
                        json=payload,
                        timeout=(30, total_timeout)  # (connect timeout, read timeout)
                    )
                    # Success - break out of retry loop
                    break
                except requests.exceptions.ReadTimeout as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"Gemini TTS API read timeout (attempt {attempt + 1}/{max_retries + 1}). Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        logger.error(f"Gemini TTS API read timeout after {total_timeout} seconds (all {max_retries + 1} attempts failed)")
                        # Provide helpful error message with suggestions
                        word_count = len(text.split())
                        char_count = len(text)
                        suggestions = []
                        if char_count > 1000:
                            suggestions.append(f"Script is {char_count} characters long. Consider splitting into smaller chunks.")
                        if video_duration and video_duration > 60:
                            suggestions.append(f"Video duration is {video_duration:.1f}s. For long videos, consider using shorter scripts.")
                        suggestions.append("Check your internet connection and API quota limits.")
                        suggestion_text = " " + " ".join(suggestions) if suggestions else ""
                        raise Exception(f"TTS generation timed out after {total_timeout} seconds after {max_retries + 1} attempts.{suggestion_text}")
                except requests.exceptions.ConnectTimeout as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"Gemini TTS API connection timeout (attempt {attempt + 1}/{max_retries + 1}). Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        logger.error(f"Gemini TTS API connection timeout after {max_retries + 1} attempts")
                        raise Exception(f"Could not connect to Gemini TTS API after {max_retries + 1} attempts. Please check your internet connection, firewall settings, and API key configuration.")
                except requests.exceptions.ConnectionError as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"Gemini TTS API connection error (attempt {attempt + 1}/{max_retries + 1}): {str(e)}. Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        logger.error(f"Gemini TTS API connection error after {max_retries + 1} attempts: {str(e)}")
                        raise Exception(f"TTS API connection failed after {max_retries + 1} attempts: {str(e)}. Please check your internet connection and API key.")
                except requests.exceptions.RequestException as e:
                    last_exception = e
                    # Don't retry for non-network errors (4xx, etc.)
                    if isinstance(e, (requests.exceptions.HTTPError, requests.exceptions.InvalidURL)):
                        logger.error(f"Gemini TTS API request error: {str(e)}")
                        raise Exception(f"TTS API request failed: {str(e)}")
                    # Retry for other network errors
                    if attempt < max_retries:
                        logger.warning(f"Gemini TTS API request error (attempt {attempt + 1}/{max_retries + 1}): {str(e)}. Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        logger.error(f"Gemini TTS API request error after {max_retries + 1} attempts: {str(e)}")
                        raise Exception(f"TTS API request failed after {max_retries + 1} attempts: {str(e)}")
            else:
                # This should not happen, but handle it just in case
                if last_exception:
                    raise Exception(f"TTS generation failed after {max_retries + 1} attempts: {str(last_exception)}")
                else:
                    raise Exception("TTS generation failed: Unknown error")
            
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
                from pipeline.utils import find_ffmpeg
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

    def _generate_comprehensive_style_prompt(self, text, speed_instruction=""):
        """
        Generate a comprehensive style prompt based on Google's TTS best practices.
        Incorporates the three levers: Style Prompt, Text Content alignment, and Markup Tags.
        Based on: https://docs.cloud.google.com/text-to-speech/docs/gemini-tts
        """
        # Analyze text content to determine emotional tone and context (Lever 2: Text Content)
        text_lower = text.lower()
        
        # Fear/suspense keywords
        fear_keywords = ['राक्षस', 'डर', 'अंधेरा', 'भय', 'साहस', 'पीछा', 'भाग', 'दौड़', 'मौत', 'खतरा', 'डरावना', 'भूत', 'चिंता']
        has_fear = any(keyword in text_lower for keyword in fear_keywords)
        
        # Exciting/energetic keywords
        exciting_keywords = ['देखो', 'वाह', 'अरे', 'मजेदार', 'रोमांचक', 'कमाल', 'जादू', 'अद्भुत', 'शानदार', 'बेहतरीन']
        has_exciting = any(keyword in text_lower for keyword in exciting_keywords)
        
        # Determine primary tone and create specific, detailed style prompt (Lever 1: Style Prompt)
        if has_fear:
            tone_description = "suspenseful, dramatic, and engaging"
            emotional_context = "narrating a suspenseful story with moments of tension and drama in Hindi"
            specific_guidance = """
- Use a dramatic, slightly tense tone when describing scary or suspenseful moments
- Use [whispering] tags strategically to create atmosphere for fear elements - whisper quietly and mysteriously
- Use [sigh] for relief, tension release, or dramatic pauses
- Maintain energy and engagement throughout - keep listeners on edge but not overwhelmed
- When text mentions fear elements, let your voice reflect genuine tension and drama
- Use [long pause] before revealing important or scary information for dramatic effect"""
        elif has_exciting:
            tone_description = "energetic, enthusiastic, and vivid"
            emotional_context = "an engaging, energetic explainer bringing scenes to life in Hindi"
            specific_guidance = """
- Speak in a friendly, vivid, and enthusiastic tone throughout
- Be genuinely enthusiastic about scenes and actions - let your excitement show
- Use [laughing] tags naturally for fun moments - react with genuine amusement and joy
- Maintain high energy and excitement - keep the pace lively and engaging
- When describing exciting events, use [short pause] to build anticipation
- Use [laughing] to react to humorous or delightful moments in the story"""
        else:
            tone_description = "friendly, engaging, and descriptive"
            emotional_context = "a friendly narrator explaining content in an engaging way in Hindi"
            specific_guidance = """
- Speak in a friendly, vivid, and descriptive tone
- Be enthusiastic about scenes and actions - bring the content to life
- Use natural pacing with appropriate pauses for clarity
- Maintain engagement throughout - keep listeners interested"""
        
        # Comprehensive style prompt incorporating all three levers (Google's best practices)
        comprehensive_prompt = f"""You are {emotional_context}. Create engaging, natural-sounding audio.

**THE THREE LEVERS OF SPEECH CONTROL (All must be aligned):**
1. **Style Prompt (Primary Driver):** {tone_description}. Natural, human-like, emotionally consistent.
2. **Text Content:** The semantic meaning of words. Match emotional delivery to the meaning (fear=tense, excitement=energetic).
3. **Markup Tags:** Bracketed tags for localized actions or style modifications. They work in concert with style and content.

**MARKUP TAG GUIDE (Based on Google's Official Documentation):**

**MODE 1: Non-speech sounds (High Reliability)**
- [sigh] - Replaced by an audible sigh sound. The tag itself is NOT spoken. Emotional quality influenced by the prompt.
- [laughing] - Replaced by an audible laugh. For best results, use with emotionally rich text. React naturally.
- [uhm] - Replaced by a hesitation sound. Useful for creating natural, conversational feel.

**MODE 2: Style modifiers (High Reliability)**
- [sarcasm] - Imparts sarcastic tone on subsequent phrase. Powerful modifier - abstract concepts can steer delivery.
- [robotic] - Makes subsequent speech sound robotic. Effect can extend across entire phrase.
- [shouting] - Increases volume of subsequent speech. Most effective when paired with matching style prompt and text that implies yelling.
- [whispering] - Decreases volume of subsequent speech. Best results when style prompt is also explicit (e.g., "whisper this part quietly").
- [extremely fast] - Increases speed of subsequent speech. Ideal for disclaimers or fast-paced dialogue.

**MODE 3: Vocalized markup (WARNING - Tag is spoken as word)**
- [scared], [curious], [bored] - These tags are SPOKEN as words AND influence tone. 
- **WARNING:** Because the tag itself is spoken, this is likely undesired for most use cases. Prefer using Style Prompt to set emotional tones instead.

**MODE 4: Pacing and pauses (High Reliability - CRITICAL)**
- [short pause] - Inserts brief pause, similar to a comma (~250ms). Use to separate clauses or list items.
- [medium pause] - Inserts standard pause, similar to a sentence break (~500ms). Effective for separating distinct sentences or thoughts.
- [long pause] - Inserts significant pause for dramatic effect (~1000ms+). Use for dramatic timing. Avoid overuse.
- **CRITICAL: Pause tags insert SILENCE into the audio. When you encounter a pause tag, you MUST STOP SPEAKING IMMEDIATELY and remain COMPLETELY SILENT for the specified duration. DO NOT SPEAK THROUGH PAUSE TAGS.**

**KEY STRATEGIES FOR RELIABLE RESULTS:**
- Align all three levers: Ensure Style Prompt, Text Content, and Markup Tags are semantically consistent.
- Use emotionally rich text: Don't rely on prompts and tags alone. Give rich, descriptive text to work with.
- Write specific, detailed prompts: More specific prompts = more reliable results.
- Respect markup tags precisely: Follow ALL tags exactly as written in the text.

{specific_guidance}

**FINAL INSTRUCTIONS:**
- Read text exactly as written, following ALL markup tags precisely.
- **PAUSE TAGS ARE MANDATORY:** When you encounter [short pause], [medium pause], or [long pause] - STOP SPEAKING IMMEDIATELY and remain COMPLETELY SILENT for the specified duration (~250ms, ~500ms, ~1000ms+ respectively).
- **DO NOT SPEAK THROUGH PAUSES. DO NOT CONTINUE TALKING. PAUSE TAGS = COMPLETE SILENCE.**
- Match emotional delivery to content meaning.
- {speed_instruction if speed_instruction else "Speak at a natural, moderate pace"}
- Maintain natural flow while respecting all markup tags."""
        
        return comprehensive_prompt
    
    def _enhance_style_prompt(self, provided_prompt, speed_instruction=""):
        """
        Enhance a provided style prompt with markup tag guidance and speed instructions.
        Based on Google's official TTS documentation.
        """
        markup_guidance = """

**MARKUP TAG GUIDE (Based on Google's Official Documentation):**

**MODE 1: Non-speech sounds (High Reliability)**
- [sigh], [laughing], [uhm] - These are replaced by actual sounds (sigh, laugh, hesitation). The tag itself is NOT spoken. React naturally.

**MODE 2: Style modifiers (High Reliability)**
- [sarcasm], [robotic], [shouting], [whispering], [extremely fast] - These modify your delivery style. Follow them precisely. Most effective when paired with matching style prompt and emotionally rich text.

**MODE 3: Vocalized markup (WARNING)**
- [scared], [curious], [bored] - These tags are SPOKEN as words AND influence tone. WARNING: The tag itself is spoken, which is likely undesired. Prefer using Style Prompt to set emotional tones instead.

**MODE 4: Pacing and pauses (High Reliability - CRITICAL)**
- [short pause] - Inserts brief pause (~250ms). Similar to a comma. Use to separate clauses.
- [medium pause] - Inserts standard pause (~500ms). Similar to a sentence break. Effective for separating distinct thoughts.
- [long pause] - Inserts significant pause (~1000ms+). Use for dramatic timing. Avoid overuse.
- **CRITICAL: Pause tags insert SILENCE into the audio. When you encounter a pause tag, you MUST STOP SPEAKING IMMEDIATELY and remain COMPLETELY SILENT for the specified duration. DO NOT SPEAK THROUGH PAUSE TAGS.**

**KEY STRATEGIES:**
- Align all three levers: Style Prompt, Text Content, and Markup Tags must be semantically consistent.
- Use emotionally rich text for best results.
- Respect markup tags precisely: Follow ALL tags exactly as written.
- **PAUSE TAGS ARE MANDATORY COMMANDS, NOT SUGGESTIONS. THEY REQUIRE COMPLETE SILENCE.**"""
        
        enhanced = f"""{provided_prompt}{markup_guidance}

**FINAL INSTRUCTIONS:**
- {speed_instruction if speed_instruction else "Speak at a natural, moderate pace"}
- Read the text exactly as written, following ALL markup tags precisely.
- **CRITICAL: When you encounter [short pause], [medium pause], or [long pause] - STOP SPEAKING IMMEDIATELY and remain COMPLETELY SILENT for the specified duration (~250ms, ~500ms, ~1000ms+ respectively). DO NOT SPEAK THROUGH PAUSES.**"""
        
        return enhanced

