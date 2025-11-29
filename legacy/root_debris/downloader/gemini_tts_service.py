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
    
    def _generate_comprehensive_style_prompt(self, text, speed_instruction=""):
        """
        Generate a comprehensive style prompt based on content analysis and TTS best practices.
        Incorporates the three levers: Style Prompt, Text Content alignment, and Markup Tags.
        """
        # Analyze text content to determine emotional tone and context
        text_lower = text.lower()
        
        # Fear/suspense keywords
        fear_keywords = ['राक्षस', 'डर', 'अंधेरा', 'भय', 'साहस', 'पीछा', 'भाग', 'दौड़', 'मौत', 'खतरा', 'डरावना', 'भूत', 'चिंता']
        has_fear = any(keyword in text_lower for keyword in fear_keywords)
        
        # Exciting/energetic keywords
        exciting_keywords = ['देखो', 'वाह', 'अरे', 'मजेदार', 'रोमांचक', 'कमाल', 'जादू', 'अद्भुत', 'शानदार', 'बेहतरीन']
        has_exciting = any(keyword in text_lower for keyword in exciting_keywords)
        
        # Determine primary tone
        if has_fear:
            tone_description = "suspenseful, dramatic, and engaging"
            emotional_context = "narrating a suspenseful story with moments of tension and drama"
            specific_guidance = """
- Use a dramatic, slightly tense tone when describing scary or suspenseful moments (राक्षस, अंधेरा, डर)
- Use [whispering] tags strategically to create atmosphere for fear elements - whisper quietly and mysteriously
- Use [sigh] for relief, tension release, or dramatic pauses
- Maintain energy and engagement throughout - keep listeners on edge but not overwhelmed
- This is entertainment content, so balance excitement with appropriate pacing
- When text mentions fear elements, let your voice reflect genuine tension and drama
- Use [long pause] before revealing important or scary information for dramatic effect"""
        elif has_exciting:
            tone_description = "energetic, enthusiastic, and vivid"
            emotional_context = "an engaging, energetic explainer bringing scenes to life"
            specific_guidance = """
- Speak in a friendly, vivid, and enthusiastic tone throughout
- Be genuinely enthusiastic about scenes and actions - let your excitement show
- Use [laughing] tags naturally for fun moments - react with genuine amusement and joy
- Maintain high energy and excitement - keep the pace lively and engaging
- When describing exciting events, use [short pause] to build anticipation
- Use [laughing] to react to humorous or delightful moments in the story"""
        else:
            tone_description = "friendly, engaging, and descriptive"
            emotional_context = "a friendly narrator explaining content in an engaging way"
            specific_guidance = """
- Speak in a friendly, vivid, and descriptive tone
- Be enthusiastic about scenes and actions - bring the content to life
- Use natural pacing with appropriate pauses for clarity
- Maintain engagement throughout - keep listeners interested"""
        
        # Comprehensive style prompt incorporating all three levers
        comprehensive_prompt = f"""You are {emotional_context} in Hindi. Your role is to create engaging and natural-sounding audio that captures the emotional essence of the content.

**PRIMARY STYLE (The Three Levers):**

1. **Style Prompt (Overall Tone):**
   - You are speaking in a {tone_description} manner
   - Your delivery should be natural, human-like, and emotionally consistent
   - Align your tone with the semantic meaning of the text content
   - Use emotionally rich delivery that matches the words being spoken

2. **Text Content Alignment:**
   - The text you are reading contains emotionally rich content
   - Match your emotional delivery to the meaning of the words
   - If the text describes fear, use a tense, dramatic tone
   - If the text describes excitement, use an enthusiastic, energetic tone
   - Let the words guide your emotional expression

3. **Markup Tags (Precise Control):**
   - Follow ALL markup tags exactly as written in the text
   - Markup tags work in concert with your style and the text content
   - Each tag has a specific behavior - respect it precisely

**MARKUP TAG GUIDANCE:**

**Mode 1: Non-speech Sounds (Replaced by audible vocalizations):**
- [sigh] - Insert a genuine sigh sound. The emotional quality (relief, tension, exhaustion) should match the context and your style prompt
- [laughing] - Insert a natural laugh. React with genuine amusement - the laugh should sound authentic and match the emotional context (amused, surprised, delighted)
- [uhm] - Insert a natural hesitation sound. Use this to create a more conversational, human-like feel

**Mode 2: Style Modifiers (Modify delivery of subsequent speech):**
- [sarcasm] - Deliver the subsequent phrase with a sarcastic tone. This is a powerful modifier - let the sarcasm be clear but not overdone
- [robotic] - Make the subsequent speech sound robotic. The effect extends across the phrase. Use sparingly and precisely
- [shouting] - Increase volume and intensity. Pair with text that implies yelling or excitement. Make it sound genuinely loud and energetic
- [whispering] - Decrease volume significantly. Speak as quietly as you can while remaining audible. Use for dramatic effect, secrets, or fear elements
- [extremely fast] - Increase speed significantly. Ideal for disclaimers or fast-paced dialogue. Maintain clarity even at high speed

**Mode 3: Pacing and Pauses (Insert silence for rhythm control):**
- [short pause] - Insert a brief pause (~250ms), similar to a comma. Use to separate clauses or list items for better clarity
- [medium pause] - Insert a standard pause (~500ms), similar to a sentence break. Effective for separating distinct sentences or thoughts
- [long pause] - Insert a significant pause (~1000ms+) for dramatic effect. Use for dramatic timing, like "The answer is... [long pause] ...no." Avoid overuse

**KEY STRATEGIES FOR RELIABLE RESULTS:**

1. **Align All Three Levers:** Ensure your Style Prompt, Text Content interpretation, and Markup Tags are all semantically consistent and working toward the same goal

2. **Use Emotionally Rich Delivery:** Don't just read the words - feel the emotions. If the text describes fear, genuinely sound tense. If it describes joy, genuinely sound happy

3. **Be Specific and Detailed:** Your delivery should be nuanced. A scared tone works best when you genuinely sound scared, not just "spooky"

4. **Respect Markup Tags Precisely:**
   - When you see [sigh], actually sigh - don't just pause
   - When you see [laughing], actually laugh - make it sound real
   - When you see [whispering], actually whisper - speak quietly and mysteriously
   - When you see [short pause], pause briefly (~250ms)
   - When you see [medium pause], pause longer (~500ms)
   - When you see [long pause], pause dramatically (~1000ms+)

5. **Natural Flow:** While following tags precisely, maintain natural speech flow. Don't sound robotic - sound human, just with precise control

{specific_guidance}

**FINAL INSTRUCTIONS:**
- Read the text exactly as written, following all markup tags precisely
- Match your emotional delivery to the content - be genuine and authentic
- Use pauses naturally - they control rhythm and pacing
- React naturally to emotional content - if something is scary, sound scared; if something is exciting, sound excited
- {speed_instruction if speed_instruction else "Speak at a natural, moderate pace"}
- Create engaging, natural-sounding audio that captures the essence of the content"""
        
        return comprehensive_prompt
    
    def _enhance_style_prompt(self, provided_prompt, speed_instruction=""):
        """
        Enhance a provided style prompt with markup tag guidance and speed instructions.
        """
        markup_guidance = """

**IMPORTANT - Markup Tag Behavior:**
- [sigh], [laughing], [uhm] - These are replaced by actual sounds (sigh, laugh, hesitation). React naturally.
- [whispering], [shouting], [sarcasm], [robotic] - These modify your delivery style. Follow them precisely.
- [short pause], [medium pause], [long pause] - These insert silence (~250ms, ~500ms, ~1000ms+ respectively). Use them for rhythm control.
- Read ALL markup tags in the text and follow them exactly as written.
- Markup tags work in concert with your style - align them with your overall tone."""
        
        enhanced = f"""{provided_prompt}{markup_guidance}
- {speed_instruction if speed_instruction else "Speak at a natural, moderate pace"}
- Read the text exactly as written, following all markup tags precisely"""
        
        return enhanced
            
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

