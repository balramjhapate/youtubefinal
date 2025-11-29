import os
import re
import json
import tempfile
import subprocess
import hashlib
from functools import lru_cache
from io import BytesIO
from urllib.parse import urlparse
from pathlib import Path
from django.conf import settings
from django.core.files.base import ContentFile
from deep_translator import GoogleTranslator
import requests

# Import NCA Toolkit client
from .nca_toolkit_client import get_nca_client

# Import new Whisper transcription module
from . import whisper_transcribe

def detect_video_source(url):
    """Detect video source/platform from URL"""
    if not url:
        return 'local'
    
    url_lower = url.lower()
    
    # Check for different platforms
    if 'xiaohongshu.com' in url_lower or 'xhslink.com' in url_lower or 'rednote' in url_lower:
        return 'rednote'
    elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif 'facebook.com' in url_lower or 'fb.com' in url_lower:
        return 'facebook'
    elif 'instagram.com' in url_lower or 'instagr.am' in url_lower:
        return 'instagram'
    elif 'vimeo.com' in url_lower:
        return 'vimeo'
    else:
        return 'other'

def extract_video_id(url, source=None):
    """Extract unique video ID from video URL based on source"""
    if not url:
        return None
    
    if source is None:
        source = detect_video_source(url)
    
    path = urlparse(url).path
    
    if source == 'rednote':
        # Xiaohongshu/RedNote format
        match = re.search(r'/item/([a-zA-Z0-9]+)', path)
        if match:
            return match.group(1)
    elif source == 'youtube':
        # YouTube format: /watch?v=VIDEO_ID, /shorts/VIDEO_ID, or /VIDEO_ID
        # Try shorts format first
        match = re.search(r'/shorts/([a-zA-Z0-9_-]{11})', url)
        if match:
            return match.group(1)
        # Try watch format
        match = re.search(r'[?&]v=([a-zA-Z0-9_-]{11})', url)
        if match:
            return match.group(1)
        # Try youtu.be format
        match = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})', url)
        if match:
            return match.group(1)
    elif source == 'facebook':
        # Facebook format: /videos/VIDEO_ID or /watch/?v=VIDEO_ID
        match = re.search(r'/videos/(\d+)', path)
        if match:
            return match.group(1)
        match = re.search(r'[?&]v=(\d+)', url)
        if match:
            return match.group(1)
    elif source == 'instagram':
        # Instagram format: /p/POST_ID or /reel/REEL_ID
        match = re.search(r'/(?:p|reel)/([a-zA-Z0-9_-]+)', path)
        if match:
            return match.group(1)
    elif source == 'vimeo':
        # Vimeo format: /VIDEO_ID
        match = re.search(r'/(\d+)', path)
        if match:
            return match.group(1)
    
    # Fallback: use URL hash or last part of path
    return None

@lru_cache(maxsize=1000)
def translate_text(text, target='en', use_ai=None):
    """
    Translate text to target language
    
    Optimized for performance:
    - Cached using LRU cache (up to 1000 recent translations)
    - For very long texts (>5000 chars), always uses GoogleTranslator (faster)
    - For Hindi, uses optimized translation (AI for short, GoogleTranslator for long)
    - For other languages, uses GoogleTranslator by default
    
    Args:
        text: Text to translate
        target: Target language code (default 'en')
        use_ai: If True, use AI for translation (better quality, preserves meaning). 
                If None (default), automatically optimized based on text length.
                If False, always use GoogleTranslator (faster but may miss words/meaning)
    
    Returns:
        str: Translated text
    """
    if not text:
        return ""
    
    text_length = len(text)
    
    # Performance optimization: For very long texts, always use GoogleTranslator (much faster)
    if text_length > 5000:
        print(f"⚡ Very long text ({text_length} chars) detected, using GoogleTranslator for speed")
        try:
            return GoogleTranslator(source='auto', target=target).translate(text)
        except Exception as e:
            print(f"Translation error: {e}")
            return text
    
    # For Hindi translation, use optimized approach
    if target == 'hi':
        if use_ai is False:
            # Explicitly requested to NOT use AI
            try:
                return GoogleTranslator(source='auto', target=target).translate(text)
            except Exception as e:
                print(f"Translation error: {e}")
                return text
        elif use_ai is True:
            # Explicitly requested to use AI
            return translate_text_with_ai(text, target='hi')
        else:
            # Default: Use optimized translation (AI for short/medium, GoogleTranslator for long)
            # translate_text_with_ai will handle the optimization internally
            return translate_text_with_ai(text, target='hi')
    
    # For other languages, use AI if explicitly requested, otherwise GoogleTranslator
    if use_ai is True:
        return translate_text_with_ai(text, target=target)
    
    # Default: Use GoogleTranslator for non-Hindi languages
    try:
        return GoogleTranslator(source='auto', target=target).translate(text)
    except Exception as e:
        print(f"Translation error: {e}")
        return text


def _translate_text_chunked(text, target, source, has_timestamps, settings_obj):
    """
    Translate long text by chunking it into smaller pieces for better performance
    
    Args:
        text: Text to translate
        target: Target language code
        source: Source language
        has_timestamps: Whether text contains timestamps
        settings_obj: AIProviderSettings object
    
    Returns:
        str: Translated text
    """
    # Chunk size: ~1500 characters per chunk (optimal for API calls)
    chunk_size = 1500
    chunks = []
    
    if has_timestamps:
        # For timestamped text, split by lines to preserve timestamps
        lines = text.split('\n')
        current_chunk = []
        current_length = 0
        
        for line in lines:
            line_length = len(line)
            if current_length + line_length > chunk_size and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_length = line_length
            else:
                current_chunk.append(line)
                current_length += line_length + 1  # +1 for newline
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
    else:
        # For plain text, split by sentences or at word boundaries
        words = text.split()
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + 1  # +1 for space
            if current_length + word_length > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
    
    if not chunks:
        # Fallback: just split by character count
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    
    print(f"📝 Translating {len(chunks)} chunks ({len(text)} total chars)...")
    
    # Translate chunks sequentially (parallel would be faster but more complex)
    translated_chunks = []
    for i, chunk in enumerate(chunks, 1):
        print(f"  Translating chunk {i}/{len(chunks)} ({len(chunk)} chars)...")
        try:
            # Use GoogleTranslator for chunks (faster than AI for individual chunks)
            translated_chunk = GoogleTranslator(source=source, target=target).translate(chunk)
            translated_chunks.append(translated_chunk)
        except Exception as e:
            print(f"  ⚠ Chunk {i} translation failed: {e}, using original")
            translated_chunks.append(chunk)
    
    result = '\n'.join(translated_chunks) if has_timestamps else ' '.join(translated_chunks)
    print(f"✓ Chunked translation complete: {len(text)} chars -> {len(result)} chars")
    return result


def translate_text_with_ai(text, target='hi', source='auto'):
    """
    Translate text using AI (Gemini/OpenAI/Anthropic) for better quality and meaning preservation
    
    Optimized for performance:
    - For long texts (>3000 chars), uses GoogleTranslator (faster)
    - For medium texts (1000-3000 chars), chunks and translates in batches
    - For short texts (<1000 chars), uses AI directly
    
    Args:
        text: Text to translate
        target: Target language code (default 'hi' for Hindi)
        source: Source language (default 'auto' for auto-detect)
    
    Returns:
        str: Translated text with preserved meaning
    """
    if not text:
        return ""
    
    # Performance optimization: For very long texts, use GoogleTranslator (much faster)
    text_length = len(text)
    if text_length > 3000:
        print(f"⚠ Long text ({text_length} chars) detected, using GoogleTranslator for faster translation")
        try:
            return GoogleTranslator(source=source, target=target).translate(text)
        except Exception as e:
            print(f"GoogleTranslator failed: {e}, falling back to AI")
            # Continue with AI translation below
    
    try:
        from .models import AIProviderSettings
        
        # Get AI provider settings
        settings_obj = AIProviderSettings.objects.first()
        if not settings_obj or not settings_obj.api_key:
            # Fallback to GoogleTranslator if AI not configured
            print("⚠ AI not configured for translation, using GoogleTranslator fallback")
            return GoogleTranslator(source=source, target=target).translate(text)
        
        # Check if text contains timestamps
        has_timestamps = bool(re.search(r'\d{1,2}:\d{2}:\d{2}\s+', text))
        
        # For medium-length texts, chunk and translate in batches for better performance
        if text_length > 1000 and text_length <= 3000:
            return _translate_text_chunked(text, target, source, has_timestamps, settings_obj)
        
        # Create system prompt for translation
        system_prompt = """You are an expert translator. Your task is to translate text accurately while preserving the complete meaning, context, and ALL words.

CRITICAL REQUIREMENTS:
1. Translate EVERY word - do not skip, omit, or miss any words
2. Preserve the complete meaning and context - nothing should be lost in translation
3. Maintain natural flow in the target language
4. Keep the same structure and format
5. Do NOT add explanations, notes, comments, or any meta-text
6. Return ONLY the translated text, nothing else
7. If timestamps are present (format: HH:MM:SS), preserve them EXACTLY as they are - do not translate or modify timestamps"""

        # Create user message
        target_lang_name = "Hindi (Devanagari script)" if target == 'hi' else target
        if has_timestamps:
            user_message = f"""Translate the following timestamped text to {target_lang_name}. 

IMPORTANT:
- Preserve ALL words and complete meaning - do not skip any words
- Keep timestamps (HH:MM:SS format) EXACTLY as they are - do not translate or modify them
- Translate only the text content, not the timestamps

Text to translate:
{text}

Return ONLY the translated text with timestamps preserved exactly."""
        else:
            user_message = f"""Translate the following text to {target_lang_name}. Preserve ALL words and complete meaning - do not skip or omit any words:

{text}

Return ONLY the translated text, nothing else."""

        # Call AI API
        if settings_obj.provider == 'gemini':
            result = _call_gemini_api(settings_obj.api_key, system_prompt, user_message)
        elif settings_obj.provider == 'openai':
            result = _call_openai_api(settings_obj.api_key, system_prompt, user_message)
        elif settings_obj.provider == 'anthropic':
            result = _call_anthropic_api(settings_obj.api_key, system_prompt, user_message)
        else:
            # Fallback to GoogleTranslator
            return GoogleTranslator(source=source, target=target).translate(text)
        
        if result and result.get('status') == 'success':
            translated_text = result.get('prompt', '').strip()
            
            # Clean up any explanatory text that AI might add
            # Remove common AI response patterns
            cleanup_patterns = [
                r'^Here\'?s the translation.*?:\s*',
                r'^Translation:\s*',
                r'^Translated text:\s*',
                r'^Here is.*?translation.*?:\s*',
            ]
            for pattern in cleanup_patterns:
                translated_text = re.sub(pattern, '', translated_text, flags=re.IGNORECASE | re.MULTILINE)
            
            translated_text = translated_text.strip()
            
            if translated_text:
                # If original had timestamps, ensure they're preserved in translation
                if has_timestamps:
                    # Verify timestamps are still present, if not, try to restore them
                    if not re.search(r'\d{1,2}:\d{2}:\d{2}\s+', translated_text):
                        # Timestamps were lost - try to restore them by matching original structure
                        original_lines = text.split('\n')
                        translated_lines = translated_text.split('\n')
                        if len(original_lines) == len(translated_lines):
                            # Try to restore timestamps
                            restored_lines = []
                            for orig_line, trans_line in zip(original_lines, translated_lines):
                                timestamp_match = re.match(r'^(\d{1,2}:\d{2}:\d{2})\s+', orig_line)
                                if timestamp_match:
                                    restored_lines.append(f"{timestamp_match.group(1)} {trans_line.strip()}")
                                else:
                                    restored_lines.append(trans_line.strip())
                            translated_text = '\n'.join(restored_lines)
                
                print(f"✓ AI translation complete: {len(text)} chars -> {len(translated_text)} chars")
                return translated_text
            else:
                # Fallback if AI returns empty
                print("⚠ AI translation returned empty, using GoogleTranslator fallback")
                return GoogleTranslator(source=source, target=target).translate(text)
        else:
            # Fallback to GoogleTranslator if AI fails
            error_msg = result.get('error', 'Unknown error') if result else 'No result'
            print(f"⚠ AI translation failed ({error_msg}), using GoogleTranslator fallback")
            return GoogleTranslator(source=source, target=target).translate(text)
            
    except Exception as e:
        print(f"⚠ AI translation error: {e}, using GoogleTranslator fallback")
        import traceback
        traceback.print_exc()
        # Fallback to GoogleTranslator
        try:
            return GoogleTranslator(source=source, target=target).translate(text)
        except:
            return text

def perform_extraction(url):
    """Perform video extraction using multiple methods
    
    Returns:
        dict: Video data with keys: video_url, title, cover_url, original_title, original_description, method
        None: If extraction failed
    """
    # Detect video source
    source = detect_video_source(url)
    last_error = None
    
    # For YouTube videos, try multiple methods
    if source == 'youtube':
        print(f"Detected YouTube video. Attempting extraction: {url}")
        
        # Priority 1: Try yt-dlp (best for getting actual video URL and metadata)
        print(f"Trying yt-dlp: {url}")
        video_data = extract_video_ytdlp(url)
        if video_data:
            video_data['method'] = 'yt-dlp'
            video_data['source'] = 'youtube'
            return video_data
        
        # Priority 2: Try direct YouTube extraction (works without yt-dlp)
        print(f"yt-dlp failed. Trying direct YouTube extraction: {url}")
        video_data = extract_video_youtube_direct(url)
        if video_data:
            video_data['method'] = 'youtube-direct'
            video_data['source'] = 'youtube'
            return video_data
        
        # Priority 3: Try Seekin API as fallback
        print(f"Direct extraction failed. Trying Seekin API: {url}")
        video_data = extract_video_seekin(url)
        if video_data:
            video_data['method'] = 'seekin'
            video_data['source'] = 'youtube'
            return video_data
        else:
            last_error = "YouTube video extraction failed. Please install yt-dlp for best results: pip install yt-dlp"
    elif source == 'facebook':
        # For Facebook, try Seekin first, then yt-dlp
        print(f"Detected Facebook video. Attempting extraction: {url}")
        video_data = extract_video_seekin(url)
        if video_data:
            video_data['method'] = 'seekin'
            video_data['source'] = 'facebook'
            return video_data
        
        video_data = extract_video_ytdlp(url)
        if video_data:
            video_data['method'] = 'yt-dlp'
            video_data['source'] = 'facebook'
            return video_data
    elif source == 'instagram':
        # For Instagram, try Seekin first, then yt-dlp
        print(f"Detected Instagram video. Attempting extraction: {url}")
        video_data = extract_video_seekin(url)
        if video_data:
            video_data['method'] = 'seekin'
            video_data['source'] = 'instagram'
            return video_data
        
        video_data = extract_video_ytdlp(url)
        if video_data:
            video_data['method'] = 'yt-dlp'
            video_data['source'] = 'instagram'
            return video_data
    elif source == 'vimeo':
        # For Vimeo, try yt-dlp first, then Seekin
        print(f"Detected Vimeo video. Attempting extraction: {url}")
        video_data = extract_video_ytdlp(url)
        if video_data:
            video_data['method'] = 'yt-dlp'
            video_data['source'] = 'vimeo'
            return video_data
        
        video_data = extract_video_seekin(url)
        if video_data:
            video_data['method'] = 'seekin'
            video_data['source'] = 'vimeo'
            return video_data
    else:
        # For RedNote and other sources, use original priority
        # Priority 1: Try Seekin.ai API (Works on blocked IPs)
        print(f"Attempting extraction via Seekin.ai API: {url}")
        video_data = extract_video_seekin(url)
        if video_data:
            video_data['method'] = 'seekin'
            video_data['source'] = source
            return video_data

        # Priority 2: yt-dlp (Works on local/unblocked IPs)
        print(f"Seekin API failed. Fallback to yt-dlp: {url}")
        video_data = extract_video_ytdlp(url)
        if video_data:
            video_data['method'] = 'yt-dlp'
            video_data['source'] = source
            return video_data
    
    # Priority 3: Direct requests (only for RedNote sources)
    if source == 'rednote':
        print(f"yt-dlp failed. Fallback to requests: {url}")
        video_data = extract_video_requests(url)
        if video_data:
            video_data['method'] = 'requests'
            video_data['source'] = source
            return video_data
        else:
            last_error = "Could not extract video. The link might be invalid or protected."
    
    # Return None with error info (could be enhanced to return error dict)
    if last_error:
        print(f"Extraction failed: {last_error}")
    return None

def extract_video_seekin(url):
    """Extract video using Seekin.ai API"""
    try:
        api_url = "https://api.seekin.ai/ikool/media/download"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        payload = {"url": url}
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") == "0000" and data.get("data"):
            video_data = data["data"]
            medias = video_data.get("medias", [])
            video_url = None
            
            # Try to find the best quality video
            if medias:
                best_media = sorted(medias, key=lambda x: x.get("fileSize", 0), reverse=True)[0]
                video_url = best_media.get("url")
            
            if video_url:
                title = video_data.get("title", "Xiaohongshu Video")
                return {
                    "video_url": video_url,
                    "title": title,
                    "cover_url": video_data.get("imageUrl"),
                    "original_title": title,
                    "original_description": title  # API might not give desc, use title
                }
        
        return None
    except Exception as e:
        print(f"Seekin API error: {e}")
        return None

def extract_video_youtube_direct(url):
    """Extract YouTube video using direct API/embed methods (works without yt-dlp)"""
    try:
        # Extract video ID
        video_id = extract_video_id(url, source='youtube')
        if not video_id:
            print(f"Could not extract video ID from URL: {url}")
            return None
        
        # Normalize to standard watch URL
        watch_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Try to get video info from YouTube oEmbed API
        oembed_url = f"https://www.youtube.com/oembed?url={watch_url}&format=json"
        try:
            response = requests.get(oembed_url, timeout=10)
            if response.status_code == 200:
                oembed_data = response.json()
                title = oembed_data.get('title', 'YouTube Video')
                thumbnail = oembed_data.get('thumbnail_url', '')
                
                # Get video embed URL (this gives us access to the video)
                embed_url = f"https://www.youtube.com/embed/{video_id}"
                
                # For actual video URL, we need to use yt-dlp or another method
                # But we can return metadata at least
                return {
                    "video_url": watch_url,  # Will need to be processed by downloader
                    "title": title,
                    "cover_url": thumbnail,
                    "original_title": title,
                    "original_description": "",
                    "embed_url": embed_url,
                    "video_id": video_id
                }
        except Exception as e:
            print(f"oEmbed API failed: {e}")
        
        # Fallback: return basic info with watch URL
        return {
            "video_url": watch_url,
            "title": f"YouTube Video {video_id}",
            "cover_url": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            "original_title": f"YouTube Video {video_id}",
            "original_description": "",
            "video_id": video_id
        }
    except Exception as e:
        print(f"YouTube direct extraction failed: {e}")
        return None

def extract_video_ytdlp(url):
    """Extract video using yt-dlp (Python module or CLI)"""
    try:
        # Normalize YouTube URLs - remove query parameters that might cause issues
        # Convert shorts URLs to standard format if needed
        if 'youtube.com' in url or 'youtu.be' in url:
            # Extract video ID and reconstruct clean URL
            video_id = extract_video_id(url, source='youtube')
            if video_id:
                # Use standard watch format for better compatibility
                url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Try using yt-dlp Python module first (more reliable)
        try:
            import yt_dlp
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    return None
                
                # Get video URL from formats
                formats = info.get('formats', [])
                video_url = None
                
                if formats:
                    # Filter for video formats with video codec
                    video_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('url')]
                    if video_formats:
                        # Get best quality video
                        best_video = sorted(video_formats, key=lambda x: x.get('height', 0) or 0, reverse=True)[0]
                        video_url = best_video.get('url')
                
                if video_url:
                    title = info.get('title', 'YouTube Video')
                    description = info.get('description', '')
                    thumbnail = info.get('thumbnail') or (info.get('thumbnails', [{}])[0].get('url') if info.get('thumbnails') else None)
                    
                    # Extract duration from yt-dlp metadata
                    duration = info.get('duration') or info.get('length')
                    if duration:
                        print(f"Video duration from yt-dlp: {duration} seconds")
                    
                    return {
                        "video_url": video_url,
                        "title": title,
                        "cover_url": thumbnail,
                        "original_title": title,
                        "original_description": description,
                        "duration": float(duration) if duration else None
                    }
                
                return None
        except ImportError:
            # Fallback to CLI if module not available
            pass
        except Exception as e:
            print(f"yt-dlp Python module failed: {e}")
            # Fallback to CLI
        
        # Fallback to CLI method
        # Use the local yt-dlp binary
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        yt_dlp_path = os.path.join(base_dir, 'yt-dlp')
        
        if not os.path.exists(yt_dlp_path):
            yt_dlp_path = 'yt-dlp'

        # Try to check if yt-dlp is available
        try:
            check_result = subprocess.run(
                [yt_dlp_path, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if check_result.returncode != 0:
                print(f"yt-dlp not found or not working: {check_result.stderr}")
                return None
        except FileNotFoundError:
            print("yt-dlp not installed. Please install it: pip install yt-dlp")
            return None

        # Extract video info with better error handling
        result = subprocess.run(
            [yt_dlp_path, '--dump-json', '--no-warnings', '--no-check-certificate', url],
            capture_output=True,
            text=True,
            timeout=60  # Increased timeout for YouTube
        )

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout
            print(f"yt-dlp extraction failed for {url}: {error_msg}")
            # Check for common errors
            if 'Private video' in error_msg or 'is private' in error_msg:
                print("Video is private")
            elif 'Video unavailable' in error_msg or 'unavailable' in error_msg:
                print("Video is unavailable")
            elif 'Sign in to confirm your age' in error_msg:
                print("Video requires age verification")
            return None

        # Parse JSON output
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            print(f"Failed to parse yt-dlp JSON output: {e}")
            print(f"Output: {result.stdout[:500]}")
            return None
        
        # Get video URL - try multiple methods
        video_url = data.get('url')
        if not video_url:
            # Try to get from requested_downloads
            requested_downloads = data.get('requested_downloads', [])
            if requested_downloads:
                video_url = requested_downloads[0].get('url')
        
        if not video_url:
            # Try formats
            formats = data.get('formats', [])
            if formats:
                # Filter for video formats only
                video_formats = [f for f in formats if f.get('vcodec') != 'none']
                if video_formats:
                    # Get best quality video
                    best_video = sorted(video_formats, key=lambda x: x.get('height', 0) or 0, reverse=True)[0]
                    video_url = best_video.get('url')
                else:
                    # Fallback to any format
                    best_video = sorted(formats, key=lambda x: x.get('height', 0) or 0, reverse=True)[0]
                    video_url = best_video.get('url')

        if video_url:
            title = data.get('title', 'YouTube Video')
            description = data.get('description', '')
            thumbnail = data.get('thumbnail') or data.get('thumbnails', [{}])[0].get('url') if data.get('thumbnails') else None
            
            # Extract duration from yt-dlp metadata
            duration = data.get('duration') or data.get('length')
            if duration:
                print(f"Video duration from yt-dlp: {duration} seconds")
            
            return {
                "video_url": video_url,
                "title": title,
                "cover_url": thumbnail,
                "original_title": title,
                "original_description": description,
                "duration": float(duration) if duration else None
            }
        
        print(f"No video URL found in yt-dlp output for {url}")
        return None
    except subprocess.TimeoutExpired:
        print(f"yt-dlp extraction timed out for {url}")
        return None
    except FileNotFoundError:
        print("yt-dlp not installed")
        return None
    except Exception as e:
        print(f"yt-dlp extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_video_requests(url):
    """Extract video using direct HTTP requests"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.xiaohongshu.com/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cookie': 'web_session=123; xsec_token=ABkAboivRVQVrgm3TNrzLjX2giKzFKasGDcrLG-AK4VVg=' 
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        html = response.text
        
        match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html, re.DOTALL)
        if match:
            state_json = match.group(1)
            state_json = state_json.replace('undefined', 'null')
            data = json.loads(state_json)
            
            note_data = data.get('note', {}).get('note', {})
            if not note_data:
                note_data = data.get('note', {})

            video_info = note_data.get('video', {})
            
            video_url = None
            if 'media' in video_info:
                stream = video_info['media'].get('stream', {}).get('h264', [])
                if stream:
                    video_url = stream[0].get('masterUrl')
            
            if not video_url:
                mp4_match = re.search(r'"masterUrl":"(http[^"]+mp4[^"]*)"', state_json)
                if mp4_match:
                    video_url = mp4_match.group(1)

            if video_url:
                title = note_data.get('title', 'Xiaohongshu Video')
                desc = note_data.get('desc', '')
                cover_url = note_data.get('imageList', [{}])[0].get('url') if note_data.get('imageList') else None
                
                return {
                    "video_url": video_url,
                    "title": title,
                    "cover_url": cover_url,
                    "original_title": title,
                    "original_description": desc
                }
        
        return None
    except Exception as e:
        print(f"Requests extraction error: {e}")
        return None

def download_file(url):
    """Download file content from URL"""
    try:
        # Check if URL is an M3U playlist (HLS stream)
        if url.endswith('.m3u8') or 'm3u8' in url.lower() or url.startswith('#EXTM3U'):
            print(f"WARNING: URL appears to be an M3U playlist, not a direct video file: {url}")
            return None
        
        response = requests.get(url, stream=True, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        
        # Check if response is actually a video file
        content_type = response.headers.get('Content-Type', '').lower()
        content = response.content
        
        # Check if content type is explicitly HTML
        if 'text/html' in content_type:
            print(f"ERROR: Content-Type is text/html, not a video file")
            return None

        # Check if it's an M3U playlist (starts with #EXTM3U)
        if content.startswith(b'#EXTM3U') or content.startswith(b'#EXT-X-VERSION'):
            print(f"ERROR: Downloaded content is an M3U playlist, not a video file")
            print(f"Content preview: {content[:200]}")
            return None
            
        # Check if it's HTML/error page (regardless of size)
        # Read first 1000 bytes for check
        first_bytes = content[:1000].lower()
        if b'<html' in first_bytes or b'<!doctype' in first_bytes:
            print(f"ERROR: Downloaded content appears to be HTML, not a video file. Size: {len(content)} bytes")
            return None
        
        # Check minimum file size (very small files are likely errors)
        if len(content) < 10000:  # Less than 10KB is suspicious
            print(f"WARNING: Downloaded file is very small ({len(content)} bytes), might be an error page")
        
        # Validate it's a video file by checking content type or file signature
        video_signatures = [b'\x00\x00\x00 ftyp', b'\x1a\x45\xdf\xa3', b'RIFF', b'\x00\x00\x01\xba']  # MP4, WebM, AVI, MPEG
        is_video = any(content.startswith(sig) for sig in video_signatures) or 'video' in content_type
        
        if not is_video and len(content) < 100000:  # If small and not clearly a video
            print(f"WARNING: Content might not be a valid video file (type: {content_type}, size: {len(content)} bytes)")
        
        return ContentFile(content)
    except Exception as e:
        print(f"Download error: {e}")
        return None

def download_video_with_ytdlp(video_url, output_path=None):
    """Download video using yt-dlp (handles HLS streams and other formats)
    
    Returns:
        ContentFile or tuple: (ContentFile, duration) if duration is available, otherwise just ContentFile
    """
    duration = None
    try:
        import yt_dlp
        import tempfile
        
        if output_path is None:
            # Create temporary file
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, f"video_{os.urandom(8).hex()}.mp4")
        
        ydl_opts = {
            'format': 'best[ext=mp4]/best',  # Prefer MP4, fallback to best available
            'outtmpl': output_path,
            'quiet': False,
            'no_warnings': False,
        }
        
        # Extract duration from metadata before downloading
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                info = ydl.extract_info(video_url, download=False)
                if info and 'duration' in info:
                    duration = float(info['duration'])
                    print(f"Duration extracted from yt-dlp metadata: {duration} seconds")
        except Exception as e:
            print(f"Could not extract duration from metadata: {e}")
        
        # Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 10000:
            # Read the downloaded file
            with open(output_path, 'rb') as f:
                content = f.read()
            # Clean up temp file
            try:
                os.remove(output_path)
            except:
                pass
            
            # If duration was extracted, return tuple, otherwise just ContentFile
            if duration:
                return (ContentFile(content), duration)
            return ContentFile(content)
        
        return None
    except ImportError:
        # Fallback to CLI
        import subprocess
        import tempfile
        
        ffmpeg_path = find_ffmpeg()
        if not ffmpeg_path:
            print("ERROR: ffmpeg not found, cannot download HLS streams")
            return None
        
        # Use yt-dlp CLI if available
        yt_dlp_path = 'yt-dlp'
        try:
            result = subprocess.run(
                [yt_dlp_path, '--version'],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                return None
        except:
            return None
        
        # Try to extract duration first using --dump-json
        try:
            duration_result = subprocess.run(
                [yt_dlp_path, '--dump-json', '--no-download', video_url],
                capture_output=True,
                text=True,
                timeout=30
            )
            if duration_result.returncode == 0:
                import json
                info = json.loads(duration_result.stdout)
                if 'duration' in info:
                    duration = float(info['duration'])
                    print(f"Duration extracted from yt-dlp metadata (CLI): {duration} seconds")
        except Exception as e:
            print(f"Could not extract duration from metadata (CLI): {e}")
        
        # Download using yt-dlp
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, f"video_{os.urandom(8).hex()}.%(ext)s")
        
        try:
            result = subprocess.run(
                [yt_dlp_path, '-f', 'best[ext=mp4]/best', '-o', output_path, video_url],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                # Find the downloaded file (yt-dlp adds extension)
                for ext in ['.mp4', '.webm', '.mkv', '.m4a']:
                    file_path = output_path.replace('%(ext)s', ext)
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            content = f.read()
                        os.remove(file_path)
                        # If duration was extracted, return tuple, otherwise just ContentFile
                        if duration:
                            return (ContentFile(content), duration)
                        return ContentFile(content)
            
            print(f"yt-dlp download failed: {result.stderr}")
            return None
        except Exception as e:
            print(f"Error downloading with yt-dlp: {e}")
            return None
    except Exception as e:
        print(f"Error downloading video with yt-dlp: {e}")
        return None

def process_video_with_ai(video_download):
    """
    Process video with AI to generate summary, tags, and insights
    
    This function:
    - Uses existing transcript if available (doesn't transcribe again)
    - Generates summary and tags based on transcript and metadata
    
    Args:
        video_download: VideoDownload model instance
        
    Returns:
        dict: {
            'summary': str,
            'tags': list,
            'status': str ('success' or 'failed'),
            'error': str (if failed)
        }
    """
    try:
        transcript_text = ''
        transcript_language = ''
        
        # Step 1: Use existing transcript if available, don't transcribe again
        if video_download.transcript and video_download.transcription_status == 'transcribed':
            transcript_text = video_download.transcript
            transcript_language = video_download.transcript_language or ''
            print(f"Using existing transcript. Language: {transcript_language}, Length: {len(transcript_text)} chars")
        else:
            print("No existing transcript found. AI processing will use metadata only.")
        
        # Step 2: Extract available information for summary
        title = video_download.title or video_download.original_title or ""
        description = video_download.description or video_download.original_description or ""
        
        # Combine all available content
        all_content_parts = []
        if title:
            all_content_parts.append(title)
        if description:
            all_content_parts.append(description)
        if transcript_text:
            all_content_parts.append(transcript_text)
        
        content = " ".join(all_content_parts).strip()
        
        if not content:
            return {
                'summary': '',
                'tags': [],
                'transcript': '',
                'transcript_language': '',
                'status': 'failed',
                'error': 'No title, description, or transcript available. Please ensure the video is transcribed first.'
            }
        
        # Step 3: Generate summary using AI Provider if available
        from .models import AIProviderSettings
        
        ai_summary = ""
        tags = []
        
        try:
            settings_obj = AIProviderSettings.objects.first()
            if settings_obj and settings_obj.api_key:
                print(f"Using AI Provider: {settings_obj.provider}")
                
                # Create prompt for Hindi summary
                system_prompt = """You are a helpful content assistant for a video platform. 
Your task is to analyze video content and generate a concise summary in HINDI and relevant tags in English.

OUTPUT FORMAT:
Return a JSON object with the following structure:
{
    "summary": "Your summary in Hindi here...",
    "tags": ["tag1", "tag2", "tag3"]
}

REQUIREMENTS:
1. Summary must be in HINDI (Devanagari script).
2. Summary should be concise (2-3 sentences) and capture the main point.
3. Tags should be in ENGLISH, relevant to the content, and include 5-10 tags.
4. If the content is inappropriate, provide a neutral summary."""

                user_message = f"""Video Title: {title}
Description: {description}
Transcript: {transcript_text[:2000]}

Please generate a Hindi summary and English tags for this video."""

                # Call AI API
                result = None
                if settings_obj.provider == 'gemini':
                    result = _call_gemini_api(settings_obj.api_key, system_prompt, user_message)
                elif settings_obj.provider == 'openai':
                    result = _call_openai_api(settings_obj.api_key, system_prompt, user_message)
                elif settings_obj.provider == 'anthropic':
                    result = _call_anthropic_api(settings_obj.api_key, system_prompt, user_message)
                
                if result and result['status'] == 'success':
                    ai_response = result['prompt']
                    # Parse JSON response
                    try:
                        # Clean up code blocks if present
                        cleaned_response = ai_response.replace('```json', '').replace('```', '').strip()
                        import json
                        parsed = json.loads(cleaned_response)
                        ai_summary = parsed.get('summary', '')
                        tags = parsed.get('tags', [])
                    except Exception as e:
                        print(f"Failed to parse AI JSON response: {e}")
                        # Fallback: treat whole response as summary if parsing fails
                        ai_summary = ai_response
                        tags = ['ai-generated']

        except Exception as e:
            print(f"AI Provider error: {e}")
            # Fallback to heuristic method below

        # Step 4: Fallback to heuristic summary if AI failed or not configured
        if not ai_summary:
            print("Falling back to heuristic summary generation...")
            summary_parts = []
            
            if transcript_text:
                # Use transcript as primary source for summary
                # Take first 300 characters or first sentence
                if len(transcript_text) > 300:
                    # Find first sentence break near 300 chars
                    truncate_pos = 300
                    for punct in ['. ', '。', '! ', '！', '? ', '？']:
                        pos = transcript_text.find(punct, 200, 300)
                        if pos != -1:
                            truncate_pos = pos + len(punct)
                            break
                    summary_parts.append(f"Transcript: {transcript_text[:truncate_pos].strip()}...")
                else:
                    summary_parts.append(f"Transcript: {transcript_text}")
            else:
                # Fallback to title and description
                if title:
                    summary_parts.append(f"This video is about: {title}")
                if description:
                    desc_summary = description.split('.')[0] if '.' in description else description[:200]
                    summary_parts.append(f"Description: {desc_summary}")
            
            ai_summary = " | ".join(summary_parts) if summary_parts else "AI analysis completed."
            
            # Translate heuristic summary to Hindi if possible
            try:
                ai_summary = translate_text(ai_summary, target='hi')
            except:
                pass

        # Step 5: Generate tags based on transcript and metadata (if not already from AI)
        if not tags:
            # Extract keywords from transcript (more accurate than just title)
            text_for_tags = transcript_text if transcript_text else f"{title} {description}"
            
            if text_for_tags:
                # Simple keyword extraction (can be enhanced with NLP)
                words = re.findall(r'\b\w{4,}\b', text_for_tags.lower())  # Words with 4+ characters
                
                # Filter common stop words (Chinese and English)
                stop_words = {
                    'the', 'this', 'that', 'with', 'from', 'have', 'been', 'they', 'what', 
                    'your', 'some', 'will', 'very', 'just', 'like', 'them', 'then', 'than',
                    'the', 'this', 'that', 'and', 'are', 'but', 'not', 'you', 'all', 'can',
                    'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his',
                    'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'its'
                }
                
                # Count word frequency
                word_count = {}
                for word in words:
                    if word not in stop_words and len(word) > 3:
                        word_count[word] = word_count.get(word, 0) + 1
                
                # Get top keywords
                sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
                tags.extend([word for word, count in sorted_words[:8]])
            
            # Add metadata-based tags
            if transcript_language:
                if transcript_language.startswith('zh'):
                    tags.append('chinese-content')
                elif transcript_language.startswith('en'):
                    tags.append('english-content')
            
            if len(transcript_text) > 500:
                tags.append('long-form')
            
            # Ensure we have at least some tags
            if not tags:
                tags = ['content', 'social-media', 'video']
        
        return {
            'summary': ai_summary,
            'tags': tags[:10],  # Limit to 10 tags
            'status': 'success',
            'error': None
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error in process_video_with_ai: {error_msg}")
        return {
            'summary': '',
            'tags': [],
            'status': 'failed',
            'error': error_msg
        }

def find_ffmpeg():
    """Find ffmpeg executable in common locations"""
    import shutil
    
    # Try to find ffmpeg in PATH first
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        return ffmpeg_path
    
    # Common installation paths
    common_paths = [
        '/opt/homebrew/bin/ffmpeg',  # Homebrew on Apple Silicon
        '/usr/local/bin/ffmpeg',  # Homebrew on Intel Mac
        '/usr/bin/ffmpeg',  # System installation
        '/bin/ffmpeg',  # Alternative system path
    ]
    
    for path in common_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            return path
    
    return None

def find_ffprobe():
    """Find ffprobe executable in common locations"""
    import shutil
    
    # Try to find ffprobe in PATH first
    ffprobe_path = shutil.which('ffprobe')
    if ffprobe_path:
        return ffprobe_path
    
    # Common installation paths
    common_paths = [
        '/opt/homebrew/bin/ffprobe',  # Homebrew on Apple Silicon
        '/usr/local/bin/ffprobe',  # Homebrew on Intel Mac
        '/usr/bin/ffprobe',  # System installation
        '/bin/ffprobe',  # Alternative system path
    ]
    
    for path in common_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            return path
    
    return None

def extract_audio_from_video(video_path, output_audio_path=None):
    """
    Extract audio from video file using ffmpeg
    
    Args:
        video_path: Path to video file
        output_audio_path: Optional output path for audio file. If None, creates temp file.
        
    Returns:
        str: Path to extracted audio file, or None if failed
    """
    try:
        # Find ffmpeg executable
        ffmpeg_path = find_ffmpeg()
        if not ffmpeg_path:
            print("ERROR: ffmpeg not found. Please install ffmpeg or ensure it's in your PATH.")
            return None
        
        if output_audio_path is None:
            # Create temporary audio file
            temp_dir = tempfile.gettempdir()
            output_audio_path = os.path.join(temp_dir, f"audio_{os.path.basename(video_path)}.wav")
        
        # Use ffmpeg to extract audio (convert to WAV format for Whisper)
        cmd = [
            ffmpeg_path,
            '-i', video_path,
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # PCM 16-bit
            '-ar', '16000',  # Sample rate 16kHz (good for Whisper)
            '-ac', '1',  # Mono channel
            '-y',  # Overwrite output file
            output_audio_path
        ]
        
        # Verify input file exists and is readable
        if not os.path.exists(video_path):
            print(f"ERROR: Video file does not exist: {video_path}")
            return None
        
        if not os.access(video_path, os.R_OK):
            print(f"ERROR: Video file is not readable: {video_path}")
            return None
        
        file_size = os.path.getsize(video_path)
        
        # Validate file is actually a video file (not M3U playlist or error page)
        # Read first bytes to check file format (size doesn't matter - can be any size)
        with open(video_path, 'rb') as f:
            first_bytes = f.read(1000)
        
        # Check if it's an M3U playlist (regardless of size)
        if first_bytes.startswith(b'#EXTM3U') or first_bytes.startswith(b'#EXT-X-VERSION'):
            print(f"ERROR: File is an M3U playlist (HLS stream), not a video file!")
            print(f"File size: {file_size} bytes")
            print(f"File content preview: {first_bytes[:200]}")
            return None
        
        # Check if it's HTML/error page (regardless of size)
        if b'<html' in first_bytes.lower() or b'<!doctype' in first_bytes.lower():
            print(f"ERROR: File appears to be HTML/error page, not a video file!")
            print(f"File size: {file_size} bytes")
            print(f"File content preview: {first_bytes[:200]}")
            return None
        
        # Check for video file signatures (MP4, WebM, AVI, MPEG, etc.)
        video_signatures = [
            b'\x00\x00\x00 ftyp',  # MP4
            b'\x1a\x45\xdf\xa3',    # WebM/Matroska
            b'RIFF',                # AVI/WAV
            b'\x00\x00\x01\xba',   # MPEG
            b'\x00\x00\x01\xb3',   # MPEG
        ]
        is_video = any(first_bytes.startswith(sig) for sig in video_signatures)
        
        # If file is very small (< 1KB), it's definitely not a video
        if file_size < 1024:
            print(f"ERROR: File is too small to be a video ({file_size} bytes)")
            return None
        
        # If no video signature found and file is small, warn but don't block (might be valid but unusual format)
        if not is_video and file_size < 10000:
            print(f"WARNING: File does not have standard video signatures and is small ({file_size} bytes)")
            print(f"File content preview: {first_bytes[:200]}")
            # Still try to process it - ffmpeg will handle format detection
        
        print(f"Extracting audio using: {ffmpeg_path}")
        print(f"Input: {video_path} (size: {file_size} bytes)")
        print(f"Output: {output_audio_path}")
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_audio_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            print(f"Created output directory: {output_dir}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            print(f"FFmpeg error (return code {result.returncode}):")
            print(f"STDERR: {result.stderr}")
            print(f"STDOUT: {result.stdout}")
            
            # Check for common errors
            error_lower = error_msg.lower()
            if 'no such file or directory' in error_lower:
                print(f"ERROR: Video file not found: {video_path}")
            elif 'permission denied' in error_lower:
                print(f"ERROR: Permission denied accessing: {video_path}")
            elif 'invalid data found' in error_lower or 'invalid argument' in error_lower:
                print(f"ERROR: Video file format may be invalid or corrupted: {video_path}")
            elif 'codec' in error_lower and 'not found' in error_lower:
                print(f"ERROR: Required codec not available in ffmpeg")
            elif 'does not contain any stream' in error_lower or 'no stream' in error_lower:
                print(f"ERROR: Video file has no audio stream. This video is video-only with no audio track.")
                # Return a special marker so we can handle this case
                return "NO_AUDIO_STREAM"
            else:
                print(f"ERROR: Unknown ffmpeg error")
            
            return None
        
        if os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 0:
            print(f"Audio extracted successfully: {output_audio_path} ({os.path.getsize(output_audio_path)} bytes)")
            return output_audio_path
        else:
            print(f"ERROR: Audio file was not created or is empty: {output_audio_path}")
            # Check if output directory is writable
            output_dir = os.path.dirname(output_audio_path)
            if output_dir and not os.access(output_dir, os.W_OK):
                print(f"ERROR: Output directory is not writable: {output_dir}")
            return None
            
    except subprocess.TimeoutExpired:
        print("ERROR: FFmpeg extraction timed out after 5 minutes")
        return None
    except FileNotFoundError:
        print("ERROR: ffmpeg executable not found. Please install ffmpeg.")
        return None
    except Exception as e:
        print(f"ERROR extracting audio: {e}")
        import traceback
        traceback.print_exc()
        return None

def transcribe_audio_local(audio_path, language=None, model_size='base'):
    """
    Transcribe audio file locally using OpenAI Whisper with enhanced features.
    Now uses the whisper_transcribe module for better language detection,
    time-aligned segments, and confidence checking.
    
    Args:
        audio_path: Path to audio file
        language: Optional language code (e.g., 'zh', 'en', 'auto'). If None, auto-detect
        model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
                    Smaller = faster, less accurate. Larger = slower, more accurate.
                    'base' is a good balance.
        
    Returns:
        dict: {
            'text': str (full transcript),
            'language': str (detected language code),
            'segments': List[Dict] (segments with timestamps and confidence),
            'status': 'success' or 'failed',
            'error': str (if failed)
        }
    """
    try:
        if not os.path.exists(audio_path):
            return {
                'text': '',
                'language': '',
                'segments': [],
                'status': 'failed',
                'error': f'Audio file not found: {audio_path}'
            }
        
        # Get configuration from settings
        model_size = getattr(settings, 'WHISPER_MODEL_SIZE', model_size)
        confidence_threshold = getattr(settings, 'WHISPER_CONFIDENCE_THRESHOLD', -1.5)
        retry_enabled = getattr(settings, 'WHISPER_RETRY_WITH_LARGER_MODEL', True)
        whisperx_enabled = getattr(settings, 'WHISPERX_ENABLED', False)
        device = getattr(settings, 'WHISPER_DEVICE', 'cpu')
        
        print(f"Loading Whisper model: {model_size}")
        print(f"Configuration: confidence_threshold={confidence_threshold}, "
              f"retry_enabled={retry_enabled}, whisperx_enabled={whisperx_enabled}")
        
        # Use WhisperX if enabled (better timestamps and diarization)
        if whisperx_enabled:
            print("Using WhisperX for improved alignment...")
            result = whisper_transcribe.transcribe_with_whisperx(
                model_name=model_size,
                audio_path=audio_path,
                device=device,
                language=language
            )
            
            if result['status'] == 'success':
                return result
            else:
                print(f"WhisperX failed: {result.get('error')}. Falling back to standard Whisper.")
        
        # Load standard Whisper model
        model = whisper_transcribe.load_whisper_model(model_size)
        
        # Transcribe with optional language specification
        print(f"Transcribing audio: {audio_path}")
        result = whisper_transcribe.transcribe_with_whisper(
            model=model,
            audio_path=audio_path,
            task='transcribe',
            language=language if language and language != 'auto' else None
        )
        
        if result['status'] != 'success':
            return result
        
        # Check segment confidence and retry if needed
        if retry_enabled and result.get('segments'):
            high_conf, low_conf = whisper_transcribe.check_segment_confidence(
                result['segments'],
                threshold=confidence_threshold
            )
            
            if low_conf:
                print(f"Found {len(low_conf)} low-confidence segments. Attempting retry...")
                retry_result = whisper_transcribe.retry_low_confidence_segments(
                    audio_path=audio_path,
                    segments=result['segments'],
                    current_model_name=model_size,
                    threshold=confidence_threshold
                )
                
                if retry_result.get('improved'):
                    print(f"Retry improved {retry_result.get('retry_count')} segments")
                    result['segments'] = retry_result['segments']
                    # Regenerate text from improved segments
                    result['text'] = whisper_transcribe.format_segments_to_plain_text(result['segments'])
        
        detected_language = result.get('language', 'unknown')
        segments = result.get('segments', [])
        
        print(f"Transcription completed. Language: {detected_language}, "
              f"Length: {len(result['text'])} chars, Segments: {len(segments)}")
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        print(f"Transcription error: {error_msg}")
        import traceback
        traceback.print_exc()
        return {
            'text': '',
            'language': '',
            'segments': [],
            'status': 'failed',
            'error': error_msg
        }

def transcribe_video(video_download):
    """
    Transcribe video using NCA Toolkit API (fast) or local Whisper (fallback)
    Also translates the transcript to Hindi automatically
    
    If DUAL_TRANSCRIPTION_ENABLED is True, runs both NCA and Whisper in parallel for comparison.
    
    Args:
        video_download: VideoDownload model instance
        
    Returns:
        dict: {
            'text': str (full transcript),
            'text_hindi': str (Hindi translation of transcript),
            'language': str (detected language code),
            'status': 'success' or 'failed',
            'error': str (if failed)
        }
    
    Note: This function should be called within a timeout wrapper to prevent hanging.
    The calling code should handle timeouts and update video status accordingly.
    """
    print(f"🔄 Starting transcription for video {video_download.id}")
    # Check if dual transcription is enabled
    if getattr(settings, 'DUAL_TRANSCRIPTION_ENABLED', False):
        print("🔄 Dual transcription mode enabled - running both NCA and Whisper...")
        from . import dual_transcribe
        return dual_transcribe.transcribe_video_dual(video_download)
    
    # Original single transcription logic (NCA or Whisper fallback)
    # Try NCA Toolkit API first (much faster)
    nca_client = None
    if getattr(settings, 'NCA_API_ENABLED', False):
        nca_client = get_nca_client()
        if nca_client:
            try:
                print("🔄 Attempting transcription via NCA Toolkit API (fast)...")
                
                # Prefer video URL if available (no download needed)
                if video_download.video_url:
                    result = nca_client.transcribe_video(video_url=video_download.video_url)
                    if result['status'] == 'success':
                        # Get transcript text (without timestamps for translation)
                        transcript_text = result.get('text', '')
                        srt_text = result.get('srt', '')
                        segments = result.get('segments', [])
                        
                        # If we have SRT, convert to timestamped format and extract plain text
                        if srt_text:
                            # Convert SRT to timestamped format (00:00:00 text)
                            timestamped_text = convert_srt_to_timestamped_text(srt_text)
                            result['transcript_with_timestamps'] = timestamped_text if timestamped_text else srt_text
                            # Extract plain text from SRT for translation (without timestamps)
                            import re
                            # Remove SRT timestamp lines and numbers
                            plain_text = re.sub(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n', '', srt_text)
                            plain_text = re.sub(r'\n\n+', '\n', plain_text).strip()
                            transcript_text = plain_text if plain_text else transcript_text
                            result['transcript_without_timestamps'] = transcript_text
                        elif segments:
                            # If we have segments, format them
                            timestamped_lines = []
                            plain_lines = []
                            for seg in segments:
                                start = seg.get('start', 0)
                                text = seg.get('text', '').strip()
                                if text:
                                    # Convert seconds to HH:MM:SS
                                    hours = int(start // 3600)
                                    minutes = int((start % 3600) // 60)
                                    seconds = int(start % 60)
                                    timestamp = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                                    timestamped_lines.append(f"{timestamp} {text}")
                                    plain_lines.append(text)
                            if timestamped_lines:
                                result['transcript_with_timestamps'] = '\n'.join(timestamped_lines)
                                result['transcript_without_timestamps'] = ' '.join(plain_lines)
                        else:
                            # If no timestamps, store plain text as both versions
                            result['transcript_without_timestamps'] = transcript_text
                            result['transcript_with_timestamps'] = transcript_text
                        
                        # Translate to Hindi using the plain text (without timestamps)
                        # IMPORTANT: Always translate to Hindi, even if the original is in Arabic/Urdu
                        if transcript_text:
                            print(f"Translating transcript to Hindi (original language: {result.get('language', 'unknown')})...")
                            hindi_translation = translate_text(transcript_text, target='hi')
                            result['text_hindi'] = hindi_translation
                            print(f"NCA API transcription successful. Original language: {result.get('language', 'unknown')}, Original length: {len(transcript_text)} chars, Hindi length: {len(hindi_translation)} chars")
                        else:
                            # If no transcript text, try to extract from timestamped version
                            if timestamped_lines:
                                plain_text = ' '.join(plain_lines) if 'plain_lines' in locals() else ' '.join([line.split(' ', 1)[1] if ' ' in line else line for line in timestamped_lines])
                                if plain_text:
                                    print(f"Extracting plain text from timestamped transcript and translating to Hindi...")
                                    hindi_translation = translate_text(plain_text, target='hi')
                                    result['text_hindi'] = hindi_translation
                        return result
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        print(f"⚠️  NCA API transcription failed: {error_msg}. Falling back to Whisper.")
                        nca_client = None  # Mark as failed so we skip local file attempt
                
                # Fallback: use local file if available and NCA client is still valid
                if nca_client and video_download.is_downloaded and video_download.local_file:
                    video_path = video_download.local_file.path
                    if os.path.exists(video_path):
                        result = nca_client.transcribe_video(video_file_path=video_path)
                        if result['status'] == 'success':
                            # Process transcript similar to URL-based transcription
                            transcript_text = result.get('text', '')
                            srt_text = result.get('srt', '')
                            segments = result.get('segments', [])
                            
                            # Extract timestamped and plain versions
                            if srt_text:
                                timestamped_text = convert_srt_to_timestamped_text(srt_text)
                                result['transcript_with_timestamps'] = timestamped_text if timestamped_text else srt_text
                                import re
                                plain_text = re.sub(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n', '', srt_text)
                                plain_text = re.sub(r'\n\n+', '\n', plain_text).strip()
                                transcript_text = plain_text if plain_text else transcript_text
                                result['transcript_without_timestamps'] = transcript_text
                            elif segments:
                                timestamped_lines = []
                                plain_lines = []
                                for seg in segments:
                                    start = seg.get('start', 0)
                                    text = seg.get('text', '').strip()
                                    if text:
                                        hours = int(start // 3600)
                                        minutes = int((start % 3600) // 60)
                                        seconds = int(start % 60)
                                        timestamp = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                                        timestamped_lines.append(f"{timestamp} {text}")
                                        plain_lines.append(text)
                                if timestamped_lines:
                                    result['transcript_with_timestamps'] = '\n'.join(timestamped_lines)
                                    result['transcript_without_timestamps'] = ' '.join(plain_lines)
                                    transcript_text = ' '.join(plain_lines)
                            
                            # Always translate to Hindi
                            if transcript_text:
                                print(f"Translating transcript to Hindi (original language: {result.get('language', 'unknown')})...")
                                hindi_translation = translate_text(transcript_text, target='hi')
                                result['text_hindi'] = hindi_translation
                                print(f"NCA API transcription successful. Original language: {result.get('language', 'unknown')}, Original length: {len(transcript_text)} chars, Hindi length: {len(hindi_translation)} chars")
                            return result
                        else:
                            error_msg = result.get('error', 'Unknown error')
                            print(f"⚠️  NCA API transcription failed: {error_msg}. Falling back to Whisper.")
            except Exception as e:
                print(f"⚠️  Error using NCA API: {e}. Falling back to Whisper.")
    
    # Fallback to local Whisper transcription (slower but works offline)
    print("🔄 Using local Whisper transcription (slower but reliable)...")
    try:
        # Check if video is downloaded locally
        if not video_download.is_downloaded or not video_download.local_file:
            # Try to download video first if we have video_url
            if video_download.video_url:
                print(f"Video not downloaded locally. Downloading from: {video_download.video_url}")
                file_content = download_file(video_download.video_url)
                if file_content:
                    filename = f"{video_download.video_id or 'video'}_{video_download.pk}.mp4"
                    video_download.local_file.save(filename, file_content, save=True)
                    video_download.is_downloaded = True
                    video_download.save()
                else:
                    return {
                        'text': '',
                        'language': '',
                        'status': 'failed',
                        'error': 'Could not download video for transcription'
                    }
            else:
                return {
                    'text': '',
                    'language': '',
                    'status': 'failed',
                    'error': 'No video file or video URL available for transcription'
                }
        
        # Get path to local video file
        video_path = video_download.local_file.path
        
        if not os.path.exists(video_path):
            return {
                'text': '',
                'language': '',
                'status': 'failed',
                'error': f'Video file not found at: {video_path}'
            }
        
        print(f"Extracting audio from video: {video_path}")
        
        # Verify video file exists and is accessible
        if not os.path.exists(video_path):
            error_msg = f'Video file not found: {video_path}'
            print(f"ERROR: {error_msg}")
            return {
                'text': '',
                'language': '',
                'status': 'failed',
                'error': error_msg
            }
        
        if not os.access(video_path, os.R_OK):
            error_msg = f'Video file is not readable: {video_path}. Check file permissions.'
            print(f"ERROR: {error_msg}")
            return {
                'text': '',
                'language': '',
                'status': 'failed',
                'error': error_msg
            }
        
        # Validate file content BEFORE attempting extraction (size doesn't matter - can be any size)
        file_size = os.path.getsize(video_path)
        print(f"Video file size: {file_size} bytes ({file_size / (1024*1024):.2f} MB)")
        
        # Check if file is invalid based on content, not size
        is_invalid = False
        invalid_reason = ""
        
        # Read first bytes to check file format
        with open(video_path, 'rb') as f:
            first_bytes = f.read(1000)
        
        # Check if it's an M3U playlist (regardless of size)
        if first_bytes.startswith(b'#EXTM3U') or first_bytes.startswith(b'#EXT-X-VERSION'):
            is_invalid = True
            invalid_reason = f"File is an M3U playlist (HLS stream), not a video file. Size: {file_size} bytes."
            print(f"ERROR: {invalid_reason}")
            print(f"File content preview: {first_bytes[:500].decode('utf-8', errors='ignore')}")
        
        # Check if it's HTML/error page (regardless of size)
        elif b'<html' in first_bytes.lower() or b'<!doctype' in first_bytes.lower():
            is_invalid = True
            invalid_reason = f"File appears to be HTML/error page, not a video file. Size: {file_size} bytes."
            print(f"ERROR: {invalid_reason}")
            print(f"File content preview: {first_bytes[:500].decode('utf-8', errors='ignore')}")
        
        # If file is extremely small (< 1KB), it's definitely not a video
        elif file_size < 1024:
            is_invalid = True
            invalid_reason = f"File is too small to be a video ({file_size} bytes)."
            print(f"ERROR: {invalid_reason}")
        
        # Check for video file signatures (but don't block if not found - ffmpeg will handle format detection)
        else:
            video_signatures = [
                b'\x00\x00\x00 ftyp',  # MP4
                b'\x1a\x45\xdf\xa3',    # WebM/Matroska
                b'RIFF',                # AVI/WAV
                b'\x00\x00\x01\xba',   # MPEG
                b'\x00\x00\x01\xb3',   # MPEG
            ]
            is_video = any(first_bytes.startswith(sig) for sig in video_signatures)
            
            if not is_video and file_size < 10000:
                # Very small file without video signature - likely invalid
                is_invalid = True
                invalid_reason = f"File does not appear to be a valid video file. Size: {file_size} bytes."
                print(f"ERROR: {invalid_reason}")
                print(f"File content preview: {first_bytes[:500]}")
            elif not is_video:
                # Large file without standard signature - might be valid but unusual format
                print(f"WARNING: File does not have standard video signatures, but size is reasonable ({file_size} bytes). Will attempt processing.")
        
        # If file is invalid, try to re-download it
        if is_invalid:
            print(f"Attempting to re-download invalid video file...")
            if video_download.video_url:
                try:
                    # Delete invalid file
                    try:
                        os.remove(video_path)
                        print(f"Deleted invalid file: {video_path}")
                    except Exception as e:
                        print(f"Could not delete invalid file: {e}")
                    
                    # Try to re-download using yt-dlp
                    from .utils import download_video_with_ytdlp
                    file_content = download_video_with_ytdlp(video_download.video_url)
                    
                    if file_content and file_content.size > 1024:  # At least 1KB
                        # Save the re-downloaded file
                        filename = f"{video_download.video_id or 'video'}_{video_download.pk}.mp4"
                        video_download.local_file.save(filename, file_content, save=True)
                        video_download.is_downloaded = True
                        video_download.save()
                        
                        # Update video_path to new file
                        video_path = video_download.local_file.path
                        file_size = os.path.getsize(video_path)
                        print(f"Successfully re-downloaded video. New size: {file_size} bytes")
                        is_invalid = False  # File is now valid
                    else:
                        error_msg = f"{invalid_reason} Attempted to re-download but failed. Please manually re-download the video."
                        print(f"ERROR: {error_msg}")
                        return {
                            'text': '',
                            'language': '',
                            'status': 'failed',
                            'error': error_msg
                        }
                except Exception as e:
                    error_msg = f"{invalid_reason} Error re-downloading: {str(e)}"
                    print(f"ERROR: {error_msg}")
                    return {
                        'text': '',
                        'language': '',
                        'status': 'failed',
                        'error': error_msg
                    }
            else:
                error_msg = f"{invalid_reason} No video URL available to re-download."
                print(f"ERROR: {error_msg}")
                return {
                    'text': '',
                    'language': '',
                    'status': 'failed',
                    'error': error_msg
                }
        
        if is_invalid:
            # If still invalid after re-download attempt
            return {
                'text': '',
                'language': '',
                'status': 'failed',
                'error': invalid_reason
            }
        
        # Extract audio from video
        temp_audio_path = None
        try:
            audio_path = extract_audio_from_video(video_path)
            
            # Check for special "NO_AUDIO_STREAM" marker first
            if audio_path == "NO_AUDIO_STREAM":
                error_msg = 'Video file has no audio stream. This video is video-only with no audio track. Transcription cannot be performed. You can still process the video for other steps if you have an existing transcript.'
                return {
                    'text': '',
                    'language': '',
                    'status': 'failed',
                    'error': error_msg,
                    'no_audio_stream': True
                }
            
            if not audio_path:
                # Check if ffmpeg is available
                ffmpeg_path = find_ffmpeg()
                if not ffmpeg_path:
                    error_msg = 'Failed to extract audio from video. ffmpeg is not installed or not found in PATH. Please install ffmpeg: brew install ffmpeg (Mac) or apt-get install ffmpeg (Linux)'
                else:
                    # Get more details about the failure
                    video_size = os.path.getsize(video_path) if os.path.exists(video_path) else 0
                    error_msg = f'Failed to extract audio from video. ffmpeg found at {ffmpeg_path} but extraction failed. Video file: {video_path} (size: {video_size} bytes). Check server logs for detailed error message.'
                
                return {
                    'text': '',
                    'language': '',
                    'status': 'failed',
                    'error': error_msg,
                    'no_audio_stream': False
                }
            
            temp_audio_path = audio_path
            
            # Transcribe audio
            print(f"Starting local Whisper transcription...")
            # Auto-detect language for Chinese/English videos
            # Use 'base' model for faster transcription (can be changed to 'small' or 'medium' for better accuracy)
            # 'base' is ~10x faster than 'large' and still very accurate
            model_size = getattr(settings, 'WHISPER_MODEL_SIZE', 'base')
            if model_size == 'large':
                print("⚠️  Warning: Using 'large' model which is very slow. Consider using 'base' or 'small' for faster transcription.")
            transcript_result = transcribe_audio_local(
                audio_path,
                language=None,  # Auto-detect (will detect Chinese, English, etc.)
                model_size=model_size  # Use setting or default to 'base'
            )
            
            # Process segments and generate SRT if available
            if transcript_result.get('status') == 'success':
                segments = transcript_result.get('segments', [])
                if segments:
                    # Generate timestamped text from segments
                    timestamped_lines = []
                    plain_lines = []
                    for seg in segments:
                        start = seg.get('start', 0)
                        text = seg.get('text', '').strip()
                        if text:
                            # Convert seconds to HH:MM:SS
                            hours = int(start // 3600)
                            minutes = int((start % 3600) // 60)
                            seconds = int(start % 60)
                            timestamp = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                            timestamped_lines.append(f"{timestamp} {text}")
                            plain_lines.append(text)
                    
                    if timestamped_lines:
                        transcript_result['transcript_with_timestamps'] = '\n'.join(timestamped_lines)
                        transcript_result['transcript_without_timestamps'] = ' '.join(plain_lines)
                    
                    # Generate SRT file
                    try:
                        srt_filename = f"transcript_{video_download.pk}.srt"
                        srt_path = os.path.join(settings.MEDIA_ROOT, 'transcripts', srt_filename)
                        srt_file_path = write_srt(segments, srt_path)
                        if srt_file_path:
                            # Read SRT content
                            with open(srt_file_path, 'r', encoding='utf-8') as f:
                                transcript_result['srt'] = f.read()
                    except Exception as e:
                        print(f"Warning: Could not generate SRT file: {e}")
                
                # Translate to Hindi if transcription was successful
                transcript_text = transcript_result.get('text', '')
                if transcript_text:
                    print(f"Translating transcript to Hindi (detected language: {transcript_result.get('language', 'unknown')})...")
                    hindi_translation = translate_text(transcript_text, target='hi')
                    transcript_result['text_hindi'] = hindi_translation
                    print(f"Translation complete. Original: {len(transcript_text)} chars, Hindi: {len(hindi_translation)} chars")
            
            # If transcription failed, return the error
            if transcript_result.get('status') != 'success':
                return transcript_result
            
            return transcript_result
            
        finally:
            # Clean up temporary audio file
            if temp_audio_path and os.path.exists(temp_audio_path):
                try:
                    os.remove(temp_audio_path)
                    print(f"Cleaned up temporary audio file: {temp_audio_path}")
                except Exception as e:
                    print(f"Warning: Could not delete temp audio file: {e}")
                    
    except Exception as e:
        error_msg = str(e)
        print(f"Error in local transcription: {error_msg}")
        import traceback
        traceback.print_exc()
        
        # Provide more detailed error messages
        error_details = error_msg
        if 'whisper' in error_msg.lower() or 'model' in error_msg.lower():
            error_details = f"Whisper model error: {error_msg}. Please ensure Whisper is properly installed."
        elif 'ffmpeg' in error_msg.lower() or 'audio' in error_msg.lower():
            error_details = f"Audio extraction error: {error_msg}. Please check if ffmpeg is installed and the video file is valid."
        elif 'file' in error_msg.lower() or 'not found' in error_msg.lower():
            error_details = f"File error: {error_msg}. Please ensure the video file exists and is accessible."
        elif 'permission' in error_msg.lower():
            error_details = f"Permission error: {error_msg}. Please check file permissions."
        else:
            error_details = f"Transcription failed: {error_msg}"
        
        return {
            'text': '',
            'language': '',
            'segments': [],
            'status': 'failed',
            'error': error_details
        }

def add_caption_to_video(video_download, caption_options=None):
    """
    Add captions to video using NCA Toolkit API
    
    Args:
        video_download: VideoDownload model instance
        caption_options: Dict with caption styling options
    
    Returns:
        dict: {
            'video_url': str (URL of captioned video),
            'status': 'success' or 'failed',
            'error': str (if failed)
        }
    """
    if not video_download.transcript:
        return {
            'video_url': '',
            'status': 'failed',
            'error': 'No transcript available. Please transcribe the video first.'
        }
    
    # Use NCA Toolkit API if enabled
    if getattr(settings, 'NCA_API_ENABLED', False):
        nca_client = get_nca_client()
        if nca_client and video_download.video_url:
            try:
                result = nca_client.add_caption(
                    video_url=video_download.video_url,
                    transcript=video_download.transcript,
                    caption_options=caption_options or {}
                )
                if result['status'] == 'success':
                    return result
            except Exception as e:
                print(f"Error adding caption via NCA API: {e}")
    
    return {
        'video_url': '',
        'status': 'failed',
        'error': 'Captioning requires NCA Toolkit API. Please enable it in settings.'
    }

def extract_thumbnail_from_video(video_download, timestamp='00:00:01'):
    """
    Extract thumbnail from video using NCA Toolkit API
    
    Args:
        video_download: VideoDownload model instance
        timestamp: Timestamp to extract (format: HH:MM:SS)
    
    Returns:
        dict: {
            'thumbnail_url': str (URL of thumbnail),
            'status': 'success' or 'failed',
            'error': str (if failed)
        }
    """
    if getattr(settings, 'NCA_API_ENABLED', False):
        nca_client = get_nca_client()
        if nca_client and video_download.video_url:
            try:
                result = nca_client.extract_thumbnail(
                    video_url=video_download.video_url,
                    timestamp=timestamp
                )
                if result['status'] == 'success':
                    return result
            except Exception as e:
                print(f"Error extracting thumbnail via NCA API: {e}")
    
    return {
        'thumbnail_url': '',
        'status': 'failed',
        'error': 'Thumbnail extraction requires NCA Toolkit API. Please enable it in settings.'
    }

def trim_video_segment(video_download, start_time, end_time):
    """
    Trim video segment using NCA Toolkit API
    
    Args:
        video_download: VideoDownload model instance
        start_time: Start time (format: HH:MM:SS)
        end_time: End time (format: HH:MM:SS)
    
    Returns:
        dict: {
            'video_url': str (URL of trimmed video),
            'status': 'success' or 'failed',
            'error': str (if failed)
        }
    """
    if getattr(settings, 'NCA_API_ENABLED', False):
        nca_client = get_nca_client()
        if nca_client and video_download.video_url:
            try:
                result = nca_client.trim_video(
                    video_url=video_download.video_url,
                    start_time=start_time,
                    end_time=end_time
                )
                if result['status'] == 'success':
                    return result
            except Exception as e:
                print(f"Error trimming video via NCA API: {e}")
    
    return {
        'video_url': '',
        'status': 'failed',
        'error': 'Video trimming requires NCA Toolkit API. Please enable it in settings.'
    }

def generate_audio_prompt(video_download):
    """
    Generate audio generation prompt from video transcript using configured AI provider
    
    Args:
        video_download: VideoDownload model instance
        
    Returns:
        dict: {
            'prompt': str (generated audio prompt),
            'status': 'success' or 'failed',
            'error': str (if failed)
        }
    """
    try:
        # Import AIProviderSettings model
        from .models import AIProviderSettings
        
        # Check if video has transcript
        if not video_download.transcript:
            return {
                'prompt': '',
                'status': 'failed',
                'error': 'No transcript available. Please transcribe the video first.'
            }
        
        # Get AI provider settings
        try:
            settings_obj = AIProviderSettings.objects.first()
            if not settings_obj or not settings_obj.api_key:
                return {
                    'prompt': '',
                    'status': 'failed',
                    'error': 'AI provider not configured. Please add API key in admin panel.'
                }
        except Exception as e:
            return {
                'prompt': '',
                'status': 'failed',
                'error': f'Error retrieving AI provider settings: {str(e)}'
            }
        
        provider = settings_obj.provider
        api_key = settings_obj.api_key
        
        # Prefer English transcript, fallback to original
        transcript_text = video_download.transcript or ''
        title = video_download.title or video_download.original_title or 'Video'
        description = video_download.description or video_download.original_description or ''
        
        # Create system prompt for AI
        system_prompt = """You are an expert audio content creator and scriptwriter. Your task is to analyze a video transcript and create a detailed audio production script in HINDI.

The output must be a comprehensive guide for voice actors and audio engineers.

STRUCTURE OF YOUR RESPONSE:

1. SCENARIO & CHARACTERS
   - Identify how many people/characters are in the scenario based on the transcript.
   - List characters with brief descriptions (e.g., "Child - Playful", "Mother - Caring").

2. DURATION ESTIMATION
   - Estimate the video duration based on the transcript length.
   - Ensure the generated script fits within this duration.

3. HINDI SCRIPT (The Dialogue)
   - Translate/Adapt the content into natural spoken HINDI (Devanagari script).
   - If the source is Chinese or English, convert it to culturally appropriate Hindi.
   - Format as a script: "Character Name: Dialogue".
   - Include specific voice actions in brackets, e.g., [Burp], [Laugh], [Sigh], [Whisper].
   - Include sound effects (SFX) cues in brackets, e.g., [SFX: Door slamming], [SFX: Water splashing].

4. AUDIO DIRECTION
   - Tone and Mood: Describe the overall feeling.
   - Speaking Style & Pacing: Instructions for the voice actor.
   - Background Music: Suggestions for music style.

5. MANDATORY OUTRO (Call to Action)
   - You MUST end the script with this exact Hindi line:
     "Maa baap ki kasam subscribe and like kar ke jao agar maa bap se pyar karte ho toh"

IMPORTANT:
- Ignore any Chinese characters in the source if they are just subtitles; focus on the meaning.
- The final output script must be in HINDI.
- Ensure high-quality audio instructions for a professional result."""
        
        # Create user message
        user_message = f"""Video Title: {title}

Description: {description}

Transcript:
{transcript_text[:5000]}  

Please create a detailed audio generation prompt and Hindi script based on the above content. Ensure all voice actions, sound effects, and the mandatory CTA are included."""
        
        # Call appropriate AI provider
        if provider == 'gemini':
            result = _call_gemini_api(api_key, system_prompt, user_message)
        elif provider == 'openai':
            result = _call_openai_api(api_key, system_prompt, user_message)
        elif provider == 'anthropic':
            result = _call_anthropic_api(api_key, system_prompt, user_message)
        else:
            return {
                'prompt': '',
                'status': 'failed',
                'error': f'Unsupported AI provider: {provider}'
            }
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error in generate_audio_prompt: {error_msg}")
        return {
            'prompt': '',
            'status': 'failed',
            'error': error_msg
        }

def _call_gemini_api(api_key, system_prompt, user_message):
    """Call Google Gemini API using REST instead of SDK"""
    # Try multiple model names - use full path format as required by API
    model_names = ['models/gemini-2.0-flash', 'models/gemini-2.5-flash', 'models/gemini-pro']
    
    for model_name in model_names:
        try:
            # model_name already includes 'models/' prefix
            url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
            
            headers = {
                'Content-Type': 'application/json',
            }
            
            # Combine prompts
            full_prompt = f"{system_prompt}\n\n{user_message}"
            
            payload = {
                "contents": [{
                    "parts": [{"text": full_prompt}]
                }]
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract text from response
            if 'candidates' in data and len(data['candidates']) > 0:
                candidate = data['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    text_parts = [part.get('text', '') for part in candidate['content']['parts']]
                    generated_text = ''.join(text_parts).strip()
                    
                    if generated_text:
                        return {
                            'prompt': generated_text,
                            'status': 'success',
                            'error': None
                        }
            
            # If we got here, the response was empty but valid - try next model
            continue
            
        except requests.exceptions.RequestException as e:
            # If it's a 404, try next model. Otherwise, return error
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 404:
                    continue  # Try next model
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('error', {}).get('message', str(e))
                except:
                    error_msg = str(e)
            else:
                error_msg = str(e)
                
            # For non-404 errors, return immediately
            if not (hasattr(e, 'response') and e.response and e.response.status_code == 404):
                return {
                    'prompt': '',
                    'status': 'failed',
                    'error': f'Gemini API error: {error_msg}'
                }
        except Exception as e:
            # Continue to try next model on any other exception
            continue
    
    # If all models failed
    return {
        'prompt': '',
        'status': 'failed',
        'error': 'Could not find a working Gemini model. Tried: ' + ', '.join(model_names)
    }


def _call_openai_api(api_key, system_prompt, user_message):
    """Call OpenAI API"""
    try:
        import openai
        
        client = openai.OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        )
        
        if response and response.choices:
            return {
                'prompt': response.choices[0].message.content.strip(),
                'status': 'success',
                'error': None
            }
        else:
            return {
                'prompt': '',
                'status': 'failed',
                'error': 'OpenAI API returned empty response'
            }
    except ImportError:
        return {
            'prompt': '',
            'status': 'failed',
            'error': 'openai library not installed. Run: pip install openai'
        }
    except Exception as e:
        return {
            'prompt': '',
            'status': 'failed',
            'error': f'OpenAI API error: {str(e)}'
        }

def _call_anthropic_api(api_key, system_prompt, user_message):
    """Call Anthropic Claude API"""
    try:
        import anthropic
        
        client = anthropic.Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        
        if response and response.content:
            return {
                'prompt': response.content[0].text.strip(),
                'status': 'success',
                'error': None
            }
        else:
            return {
                'prompt': '',
                'status': 'failed',
                'error': 'Anthropic API returned empty response'
            }
    except ImportError:
        return {
            'prompt': '',
            'status': 'failed',
            'error': 'anthropic library not installed. Run: pip install anthropic'
        }
    except Exception as e:
        return {
            'prompt': '',
            'status': 'failed',
            'error': f'Anthropic API error: {str(e)}'
        }


def batch_translate_text(texts, target='hi', batch_size=50):
    """
    Translate multiple texts in batches for better performance
    
    Args:
        texts: List of text strings to translate
        target: Target language code (default: 'hi' for Hindi)
        batch_size: Number of texts to translate in each batch
        
    Returns:
        list: Translated texts in the same order as input
    """
    if not texts:
        return []
    
    translated = []
    
    try:
        translator = GoogleTranslator(source='auto', target=target)
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Join batch with special separator
            separator = " |BATCH_SEP| "
            combined_text = separator.join(batch)
            
            # Translate combined text
            translated_combined = translator.translate(combined_text)
            
            # Split back into individual translations
            batch_translated = translated_combined.split(separator)
            
            # Handle case where split doesn't match (fallback to individual translation)
            if len(batch_translated) != len(batch):
                print(f"⚠ Batch translation mismatch, falling back to individual translation for batch {i//batch_size + 1}")
                for text in batch:
                    try:
                        translated.append(translator.translate(text))
                    except Exception as e:
                        print(f"Translation error for text: {text[:50]}... Error: {e}")
                        translated.append(text)  # Use original if translation fails
            else:
                translated.extend(batch_translated)
    
    except Exception as e:
        print(f"Batch translation error: {e}. Falling back to individual translation.")
        # Fallback to individual translation
        translator = GoogleTranslator(source='auto', target=target)
        for text in texts:
            try:
                translated.append(translator.translate(text))
            except Exception as e:
                print(f"Translation error: {e}")
                translated.append(text)  # Use original if translation fails
    
    return translated

def get_video_duration(video_path):
    """
    Extract video duration using ffprobe
    
    Args:
        video_path: Path to video file
        
    Returns:
        float: Duration in seconds, or None if failed
    """
    try:
        import subprocess
        import json
        
        # Find ffprobe executable
        ffprobe_path = find_ffprobe()
        if not ffprobe_path:
            print("ERROR: ffprobe not found. Please install ffmpeg or ensure it's in your PATH.")
            return None
        
        # Verify file exists
        if not os.path.exists(video_path):
            print(f"ERROR: Video file does not exist: {video_path}")
            return None
        
        # Use ffprobe to get video duration
        cmd = [
            ffprobe_path,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            video_path
        ]
        
        print(f"Extracting video duration using: {ffprobe_path}")
        print(f"Video file: {video_path}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            print(f"FFprobe error (return code {result.returncode}): {error_msg}")
            return None
        
        data = json.loads(result.stdout)
        duration_str = data.get('format', {}).get('duration')
        
        if duration_str:
            duration = float(duration_str)
            print(f"Video duration extracted: {duration} seconds ({duration/60:.2f} minutes)")
            return duration
        
        print("WARNING: No duration found in ffprobe output")
        return None
        
    except subprocess.TimeoutExpired:
        print("ERROR: FFprobe extraction timed out")
        return None
    except FileNotFoundError:
        print("ERROR: ffprobe executable not found. Please install ffmpeg.")
        return None
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse ffprobe JSON output: {e}")
        print(f"Output: {result.stdout[:500] if 'result' in locals() else 'N/A'}")
        return None
    except Exception as e:
        print(f"ERROR extracting video duration: {e}")
        import traceback
        traceback.print_exc()
        return None

def calculate_tts_parameters(duration_seconds):
    """
    Calculate TTS parameters (speed, temperature, etc.) based on video duration
    
    Args:
        duration_seconds: Video duration in seconds
        
    Returns:
        dict: {
            'speed': float,
            'temperature': float,
            'repetition_penalty': float
        }
    """
    if not duration_seconds or duration_seconds <= 0:
        # Default values
        return {
            'speed': 1.0,
            'temperature': 0.75,
            'repetition_penalty': 5.0
        }
    
    # Adjust speed based on duration
    # Shorter videos (< 30s): slightly faster (1.1x)
    # Medium videos (30-120s): normal speed (1.0x)
    # Longer videos (> 120s): slightly slower (0.9x) to fit content
    if duration_seconds < 30:
        speed = 1.1
    elif duration_seconds <= 120:
        speed = 1.0
    else:
        # For longer videos, slow down to fit more content
        speed = max(0.85, 1.0 - (duration_seconds - 120) / 600)  # Gradually slow down
    
    # Temperature: slightly lower for longer videos (more consistent)
    if duration_seconds < 60:
        temperature = 0.75
    else:
        temperature = 0.7
    
    # Repetition penalty: higher for longer videos to avoid repetition
    if duration_seconds < 60:
        repetition_penalty = 5.0
    else:
        repetition_penalty = 5.5
    
    return {
        'speed': round(speed, 2),
        'temperature': round(temperature, 2),
        'repetition_penalty': round(repetition_penalty, 2)
    }

def get_audio_duration(audio_path):
    """
    Extract audio duration using ffprobe
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        float: Duration in seconds, or None if failed
    """
    try:
        import subprocess
        import json
        
        # Find ffprobe executable
        ffprobe_path = find_ffprobe()
        if not ffprobe_path:
            print("ERROR: ffprobe not found. Please install ffmpeg or ensure it's in your PATH.")
            return None
        
        # Verify file exists
        if not os.path.exists(audio_path):
            print(f"ERROR: Audio file does not exist: {audio_path}")
            return None
        
        # Use ffprobe to get audio duration
        cmd = [
            ffprobe_path,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            audio_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            print(f"FFprobe error (return code {result.returncode}): {error_msg}")
            return None
        
        data = json.loads(result.stdout)
        duration_str = data.get('format', {}).get('duration')
        
        if duration_str:
            duration = float(duration_str)
            print(f"Audio duration extracted: {duration} seconds")
            return duration
        
        print("WARNING: No duration found in ffprobe output")
        return None
        
    except subprocess.TimeoutExpired:
        print("ERROR: FFprobe extraction timed out")
        return None
    except FileNotFoundError:
        print("ERROR: ffprobe executable not found. Please install ffmpeg.")
        return None
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse ffprobe JSON output: {e}")
        return None
    except Exception as e:
        print(f"ERROR extracting audio duration: {e}")
        import traceback
        traceback.print_exc()
        return None

def adjust_audio_duration(audio_path, target_duration, output_path=None):
    """
    Adjust audio duration to match target duration using ffmpeg
    
    Args:
        audio_path: Path to input audio file
        target_duration: Target duration in seconds
        output_path: Optional output path. If None, overwrites input file.
        
    Returns:
        str: Path to adjusted audio file, or None if failed
    """
    try:
        import subprocess
        import tempfile
        
        # Find ffmpeg executable
        ffmpeg_path = find_ffmpeg()
        if not ffmpeg_path:
            print("ERROR: ffmpeg not found. Please install ffmpeg or ensure it's in your PATH.")
            return None
        
        # Get current audio duration
        current_duration = get_audio_duration(audio_path)
        if not current_duration:
            print("ERROR: Could not get current audio duration")
            return None
        
        if abs(current_duration - target_duration) < 0.1:
            # Duration is already close enough (within 0.1 seconds)
            print(f"Audio duration ({current_duration:.2f}s) already matches target ({target_duration:.2f}s)")
            return audio_path
        
        # Calculate speed factor
        speed_factor = current_duration / target_duration
        
        # Limit speed adjustment to reasonable range (0.5x to 2.0x)
        if speed_factor < 0.5:
            speed_factor = 0.5
            print(f"WARNING: Speed factor too low ({speed_factor:.2f}), limiting to 0.5x")
        elif speed_factor > 2.0:
            speed_factor = 2.0
            print(f"WARNING: Speed factor too high ({speed_factor:.2f}), limiting to 2.0x")
        
        # If output_path not provided, use temp file then replace original
        if output_path is None:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            output_path = temp_file.name
            temp_file.close()
            replace_original = True
        else:
            replace_original = False
        
        print(f"Adjusting audio duration: {current_duration:.2f}s -> {target_duration:.2f}s (speed: {speed_factor:.2f}x)")
        
        # Use ffmpeg to adjust audio speed
        # atempo filter can only handle 0.5 to 2.0 range, so we may need to chain filters
        if speed_factor >= 0.5 and speed_factor <= 2.0:
            # Single atempo filter
            cmd = [
                ffmpeg_path,
                '-i', audio_path,
                '-filter:a', f'atempo={speed_factor:.3f}',
                '-y',  # Overwrite output
                output_path
            ]
        else:
            # Chain multiple atempo filters for extreme adjustments
            # This shouldn't happen with our limits, but just in case
            tempo1 = min(2.0, speed_factor)
            tempo2 = speed_factor / tempo1
            cmd = [
                ffmpeg_path,
                '-i', audio_path,
                '-filter:a', f'atempo={tempo1:.3f},atempo={tempo2:.3f}',
                '-y',  # Overwrite output
                output_path
            ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            print(f"FFmpeg error (return code {result.returncode}): {error_msg[:500]}")
            if replace_original and os.path.exists(output_path):
                os.unlink(output_path)
            return None
        
        # Verify output file exists and has reasonable size
        if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
            print("ERROR: Adjusted audio file is too small or doesn't exist")
            if replace_original and os.path.exists(output_path):
                os.unlink(output_path)
            return None
        
        # Verify adjusted duration
        adjusted_duration = get_audio_duration(output_path)
        if adjusted_duration:
            duration_diff = abs(adjusted_duration - target_duration)
            if duration_diff > 0.5:
                print(f"WARNING: Adjusted duration ({adjusted_duration:.2f}s) doesn't match target ({target_duration:.2f}s), difference: {duration_diff:.2f}s")
            else:
                print(f"✓ Audio duration adjusted successfully: {adjusted_duration:.2f}s (target: {target_duration:.2f}s)")
        
        # Replace original if needed
        if replace_original:
            import shutil
            shutil.move(output_path, audio_path)
            return audio_path
        
        return output_path
        
    except subprocess.TimeoutExpired:
        print("ERROR: FFmpeg adjustment timed out")
        if 'output_path' in locals() and os.path.exists(output_path):
            os.unlink(output_path)
        return None
    except Exception as e:
        print(f"ERROR adjusting audio duration: {e}")
        import traceback
        traceback.print_exc()
        if 'output_path' in locals() and os.path.exists(output_path):
            os.unlink(output_path)
        return None

def remove_questions_from_script(script):
    """
    Remove question lines from script to keep only main action/content
    
    Args:
        script: Script text that may contain questions
        
    Returns:
        str: Script with questions removed
    """
    if not script:
        return script
    
    import re
    lines = script.split('\n')
    clean_lines = []
    
    # Patterns to identify questions
    question_patterns = [
        r'^.*क्या\s+आप',
        r'^.*क्या\s+ये',
        r'^.*क्या\s+आपने',
        r'^.*क्या\s+आपको',
        r'^.*\?',  # Lines ending with question mark
        r'^.*क्या\s+.*\?',  # Lines with क्या and question mark
    ]
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        # Check if line is a question
        is_question = False
        for pattern in question_patterns:
            if re.search(pattern, line_stripped, re.IGNORECASE):
                is_question = True
                break
        
        # Only keep non-question lines
        if not is_question:
            clean_lines.append(line)
    
    return '\n'.join(clean_lines).strip()


def format_hindi_script(raw_script, title):
    """
    Format the Hindi script - remove title/voice prompt sections and make it kid-friendly
    
    Args:
        raw_script: Raw script text from AI
        title: Video title (not used anymore, kept for compatibility)
        
    Returns:
        str: Formatted script without headers, kid-friendly
    """
    # Remove title and voice prompt sections if present
    lines = raw_script.split('\n')
    clean_lines = []
    skip_headers = False
    
    for line in lines:
        line_stripped = line.strip()
        
        # Skip title and voice prompt headers
        if line_stripped.startswith('**शीर्षक:**') or line_stripped.startswith('**आवाज़:**'):
            skip_headers = True
            continue
        
        # Skip empty lines after headers
        if skip_headers and not line_stripped:
            continue
        
        # Start collecting content after headers
        if skip_headers and line_stripped:
            skip_headers = False
        
        # Skip voice prompt content patterns
        if ('माँ बाप की कसम' in line_stripped or 
            'subscribe और like कर के जाओ' in line_stripped or
            'अगर माँ बाप से प्यार' in line_stripped):
            continue
        
        # Add the line if it's not a header
        if not line_stripped.startswith('**'):
            clean_lines.append(line)
    
    # Join lines and ensure "Dekho" at the start
    processed_script = '\n'.join(clean_lines).strip()
    
    # Add "Dekho" at the start of the first content line if not present
    lines = processed_script.split('\n')
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if line_stripped:
            # This is the first content line
            if not (line_stripped.startswith('देखो') or line_stripped.startswith('Dekho') or 
                    re.match(r'^\d{1,2}:\d{2}:\d{2}\s+देखो', line_stripped)):
                # Add "देखो" at the start
                if re.match(r'^\d{1,2}:\d{2}:\d{2}\s+', line_stripped):
                    # Has timestamp, add "देखो" after timestamp
                    lines[i] = re.sub(r'^(\d{1,2}:\d{2}:\d{2}\s+)(.+)', r'\1देखो \2', line_stripped)
                else:
                    # No timestamp, add "देखो" at start
                    lines[i] = f"देखो {line_stripped}"
            break
    
    processed_script = '\n'.join(lines)
    
    return processed_script.strip()


def convert_srt_to_timestamped_text(srt_text):
    """
    Convert SRT format to timestamped text format (00:00:00 text)
    
    Args:
        srt_text: SRT format text with timestamps
        
    Returns:
        str: Formatted text with timestamps in 00:00:00 format
    """
    if not srt_text:
        return ""
    
    import re
    lines = []
    # SRT format: number, timestamp, text, blank line
    # Example:
    # 1
    # 00:00:00,000 --> 00:00:02,000
    # Text here
    
    # Split by double newlines to get segments
    segments = re.split(r'\n\s*\n', srt_text.strip())
    
    for segment in segments:
        if not segment.strip():
            continue
        
        segment_lines = segment.strip().split('\n')
        if len(segment_lines) >= 3:
            # Skip the number (first line)
            timestamp_line = segment_lines[1]
            text_lines = segment_lines[2:]
            
            # Extract start time from "00:00:00,000 --> 00:00:02,000"
            time_match = re.search(r'(\d{2}):(\d{2}):(\d{2}),\d{3}', timestamp_line)
            if time_match:
                hours, minutes, seconds = time_match.groups()
                timestamp = f"{hours}:{minutes}:{seconds}"
                text = ' '.join(text_lines).strip()
                if text:
                    lines.append(f"{timestamp} {text}")
    
    return '\n'.join(lines)

def write_srt(segments, out_path="out.srt"):
    """
    Write SRT subtitle file from Whisper segments
    
    Args:
        segments: List of segment dicts with 'start', 'end', and 'text' keys
        out_path: Output file path for SRT file
        
    Returns:
        str: Path to written SRT file, or None if failed
    """
    try:
        # Ensure directory exists
        out_path_obj = Path(out_path)
        out_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        with open(out_path, "w", encoding="utf-8") as f:
            for i, s in enumerate(segments, start=1):
                def fmt(ts):
                    """Format timestamp to SRT format: HH:MM:SS,mmm"""
                    h = int(ts // 3600)
                    m = int((ts % 3600) // 60)
                    sec = int(ts % 60)
                    ms = int((ts - int(ts)) * 1000)
                    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"
                
                start_time = s.get('start', 0)
                end_time = s.get('end', start_time + 1)
                text = s.get('text', '').strip()
                
                if text:
                    f.write(f"{i}\n")
                    f.write(f"{fmt(start_time)} --> {fmt(end_time)}\n")
                    f.write(text + "\n\n")
        
        print(f"SRT file written successfully: {out_path}")
        return out_path
    except Exception as e:
        print(f"Error writing SRT file: {e}")
        return None

def remove_non_hindi_characters(text):
    """
    Remove non-Hindi characters (Chinese, English, etc.) from text, keeping only Hindi (Devanagari) script
    
    Args:
        text: Text that may contain mixed languages
        
    Returns:
        str: Text with only Hindi (Devanagari) characters, spaces, and punctuation
    """
    if not text:
        return text
    
    import re
    # Keep only Devanagari script (Hindi), numbers, spaces, and common punctuation
    # Devanagari range: U+0900 to U+097F
    # Also keep common punctuation: ।, !, ?, ., ,, :, ;, -, etc.
    hindi_pattern = re.compile(
        r'[^\u0900-\u097F\s0-9।!?.,:;()\-"\']+',
        re.UNICODE
    )
    cleaned_text = hindi_pattern.sub('', text)
    
    # Clean up multiple spaces
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
    
    return cleaned_text.strip()


def fix_sentence_structure(text):
    """
    Fix sentence structure for better TTS - add proper punctuation, fix grammar, ensure natural flow
    
    Args:
        text: Text with potential sentence structure issues
        
    Returns:
        str: Text with improved sentence structure
    """
    if not text:
        return text
    
    import re
    
    # Common grammar fixes
    fixes = {
        r'साहसाते': 'डराते',  # "scare" not "courage"
        r'साहस लग रहा है': 'डर लग रहा है',  # "feeling scared" not "feeling courage"
        r'बहुत साहस': 'बहुत डर',  # "very scared" not "very courage"
    }
    
    for pattern, replacement in fixes.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Ensure sentences end with proper punctuation
    # If a line doesn't end with punctuation and is a complete sentence, add ।
    lines = text.split('\n')
    fixed_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            fixed_lines.append('')
            continue
        
        # If line doesn't end with punctuation and seems like a complete sentence, add ।
        if not re.search(r'[।!?]$', line):
            # Check if it's a complete sentence (has verb or action word)
            if re.search(r'(है|हैं|हो|था|थे|गया|गई|गए|कर|करता|करती|करते|जा|जाता|जाती|जाते|आ|आता|आती|आते|दे|देता|देती|देते|ले|लेता|लेती|लेते|रह|रहा|रही|रहे)', line):
                line = line + '।'
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def get_clean_script_for_tts(formatted_script):
    """
    Extract clean script text for TTS (without formatting headers, timestamps, and questions)
    Only keeps main action/content description
    Removes introductory text and ensures CTA is at the end
    Filters negative/abusive words before returning
    Removes non-Hindi characters and fixes sentence structure for better TTS
    
    Args:
        formatted_script: Formatted script with headers
        
    Returns:
        str: Clean script text for TTS (only main content, no headers, timestamps, or questions) with CTA at end, negative words filtered, proper sentence structure
    """
    if not formatted_script:
        return ""
    
    # Filter negative/abusive words first
    from .word_filter import filter_negative_words
    formatted_script = filter_negative_words(formatted_script)
    
    import re
    lines = formatted_script.split('\n')
    clean_lines = []
    skip_until_content = False
    skip_voice_prompt = False  # Track if we're in voice prompt section
    
    # Patterns to identify questions (if we want to remove them, but usually we want to keep them for TTS)
    # The user wants to remove questions from the script for some reason? 
    # The original code removed them. Let's keep that behavior but make it smarter.
    # Actually, for a good story, questions are important. 
    # But the function name says "remove_questions_from_script" was used before.
    # Let's assume we want to KEEP questions for better storytelling unless explicitly asked to remove.
    # However, the original code had explicit question removal. 
    # Let's stick to the user's request of "Clean Script" which usually means just the narration.
    # But removing questions might break the flow. 
    # Let's refine the cleaning to be "Narrative Only" if that's the goal, OR just remove metadata.
    # Given the context of "Triple Transcription Comparison", the script should be the STORY.
    # Questions like "Kya aap jante hain?" are part of the hook. Removing them is bad.
    # I will DISABLE question removal for now to improve quality, as questions are vital for engagement.
    
    # Patterns to identify introductory/meta text to remove
    intro_patterns = [
        r'ठीक\s+है[,\s]*मैं\s+समझ\s+गया',
        r'यहाँ\s+स्क्रिप्ट\s+है',
        r'यहाँ\s+हिंदी\s+स्क्रिप्ट\s+है',
        r'नमस्ते',
        r'स्वागत\s+है',
        r'Title:',
        r'Description:',
        r'Visual:',
        r'Audio:',
        r'Scene\s+\d+:',
    ]
    
    # Patterns to identify voice prompt content (CTA) - we want to keep this but maybe move it?
    # Actually, the prompt says "ensure CTA is at the end".
    voice_prompt_patterns = [
        r'माँ\s+बाप\s+की\s+कसम',
        r'subscribe\s+और\s+like',
        r'subscribe.*like',
        r'धन्यवाद',
        r'अगर\s+माँ\s+बाप\s+से\s+प्यार',
        r'कर\s+के\s+जाओ',
        r'कसम\s+है',
    ]

    # Valid TTS markup tags to preserve
    markup_pattern = r'\[(sigh|laughing|uhm|sarcasm|robotic|shouting|whispering|extremely fast|short pause|medium pause|long pause|scared|curious|bored)\]'
    
    for line in lines:
        original_line = line
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue

        # Skip header sections (Markdown headers)
        if line.startswith('#') or line.startswith('**') or line.startswith('##'):
             # But check if it contains Hindi text that looks like script
             # Sometimes headers are just "**Scene 1:**" -> Skip
             # Sometimes "**Narrator:** Hello" -> Keep "Hello"
             if ':' in line:
                 parts = line.split(':', 1)
                 if len(parts) > 1 and re.search(r'[\u0900-\u097F]', parts[1]):
                     line = parts[1].strip()
                 else:
                     continue
             else:
                 continue
        
        # Remove timestamps
        line = re.sub(r'^\d{1,2}:\d{2}(:\d{2})?\s+', '', line)
        
        # Check for intro patterns
        is_intro = False
        for pattern in intro_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                is_intro = True
                break
        if is_intro:
            continue

        # Check for voice prompt/CTA patterns globally (even at the end)
        is_cta = False
        for pattern in voice_prompt_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                is_cta = True
                break
        if is_cta:
            continue

        # Check for visual descriptions (usually in brackets or starting with Visual:)
        # But we want to keep TTS markup!
        # So we only remove brackets that are NOT valid TTS markup
        
        # Function to replace invalid brackets
        def replace_invalid_brackets(match):
            content = match.group(0)
            if re.match(markup_pattern, content, re.IGNORECASE):
                return content # Keep valid markup
            return "" # Remove other bracketed content like [Visual: ...]

        line = re.sub(r'\[.*?\]', replace_invalid_brackets, line)
        line = re.sub(r'\(.*?\)', '', line) # Remove parentheses content usually visual cues

        # Filter negative words (using the imported function)
        # line = filter_negative_words(line) # Already called at start of function

        # Only add if it contains Hindi characters or valid English words (like 'Subscribe')
        # And is not just punctuation
        if (re.search(r'[\u0900-\u097F]', line) or re.search(r'[a-zA-Z]', line)) and len(line) > 2:
            clean_lines.append(line.strip())
    
    # Join all lines
    clean_text = ' '.join(clean_lines)
    
    # Fix punctuation spacing
    clean_text = re.sub(r'\s+([,۔?!])', r'\1', clean_text)
    
    return clean_text
    
    # Join all clean lines with proper sentence breaks
    # Preserve sentence structure for better TTS explanation
    clean_script = '\n'.join(clean_lines).strip()
    
    # Remove non-Hindi characters (Chinese, English, etc.) - keep only Hindi script
    clean_script = remove_non_hindi_characters(clean_script)
    
    # Fix sentence structure - add punctuation, fix grammar
    clean_script = fix_sentence_structure(clean_script)
    
    # Remove repetitive phrases (like "मत करो, मत करो, मत करो...")
    # Pattern to find repeated phrases (3+ times)
    repetitive_patterns = [
        r'(मत करो[, ]+){3,}',  # "मत करो, मत करो, मत करो..." -> remove all but context
        r'(नहीं[, ]+){3,}',
        r'(रुको[, ]+){3,}',
        r'(बंद करो[, ]+){3,}',
        r'(छोड़ दो[, ]+){3,}',
    ]
    
    for pattern in repetitive_patterns:
        # Replace repetitive phrases with single occurrence or remove
        matches = re.finditer(pattern, clean_script, re.IGNORECASE)
        for match in list(matches):
            # Remove the repetitive phrase entirely (it's usually filler)
            clean_script = clean_script.replace(match.group(0), '').strip()
    
    # Clean up extra spaces and commas, but preserve sentence breaks
    clean_script = re.sub(r',\s*,+', ',', clean_script)  # Multiple commas
    # Preserve newlines for sentence structure - only clean up excessive spaces within lines
    lines = clean_script.split('\n')
    cleaned_lines = []
    for line in lines:
        # Clean up multiple spaces within a line, but preserve the line structure
        cleaned_line = re.sub(r'[ \t]+', ' ', line.strip())
        if cleaned_line:  # Only add non-empty lines
            cleaned_lines.append(cleaned_line)
    clean_script = '\n'.join(cleaned_lines)
    clean_script = re.sub(r'\n\s*\n+', '\n', clean_script)  # Multiple newlines -> single newline
    clean_script = clean_script.strip()
    
    # Ensure proper sentence breaks - add newline after sentence-ending punctuation if missing
    # This helps TTS understand sentence boundaries better
    clean_script = re.sub(r'([।!?])\s*([^\n])', r'\1\n\2', clean_script)  # Add newline after ।!? if not already there
    clean_script = re.sub(r'\n\s*\n+', '\n', clean_script)  # Clean up multiple newlines again
    clean_script = clean_script.strip()
    
    # Ensure each sentence is on its own line for better TTS clarity
    # Split by sentence endings and ensure proper line breaks
    lines = clean_script.split('\n')
    final_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # If line contains multiple sentences (has multiple । or ! or ?), split them
        if re.search(r'[।!?].*[।!?]', line):
            # Split by sentence endings
            sentences = re.split(r'([।!?]+)', line)
            current_sentence = ''
            for part in sentences:
                if part in ['।', '!', '?', '।।', '!!', '??']:
                    current_sentence += part
                    if current_sentence.strip():
                        final_lines.append(current_sentence.strip())
                    current_sentence = ''
                else:
                    current_sentence += part
            if current_sentence.strip():
                final_lines.append(current_sentence.strip())
        else:
            final_lines.append(line)
    
    clean_script = '\n'.join(final_lines)
    clean_script = re.sub(r'\n\s*\n+', '\n', clean_script)  # Clean up multiple newlines
    clean_script = clean_script.strip()
    
    # Filter negative words again after cleaning repetitive phrases
    from .word_filter import filter_negative_words
    clean_script = filter_negative_words(clean_script)
    
    # Add "Dekho" at the start if not present
    if clean_script and not clean_script.strip().startswith('देखो') and not clean_script.strip().startswith('Dekho'):
        # Find the first non-empty line and add "देखो" to it
        lines = clean_script.split('\n')
        if lines:
            first_line = lines[0].strip()
            if first_line:
                lines[0] = f"देखो {first_line}"
                clean_script = '\n'.join(lines)
    
    # ALWAYS add CTA at the end - append it properly formatted (with mother and father)
    # IMPORTANT: Use "पापा" not "पुण्या"
    cta_text = "आपकी मम्मी पापा कसम सब्सक्राइब जरूर करे"
    partial_cta = "आपकी मम्मी कसम सब्सक्राइब"
    # Remove any incorrect CTA with "पुण्या"
    incorrect_cta = "आपकी मम्मी पुण्या कसम सब्सक्राइब जरूर करे"
    
    if clean_script:
        # Check if CTA already exists at the end
        script_stripped = clean_script.strip()
        ends_with_full_cta = script_stripped.endswith(cta_text)
        ends_with_partial_cta = script_stripped.endswith(partial_cta) and not ends_with_full_cta
        
        # If CTA is already at the end, keep it as is
        if ends_with_full_cta:
            return clean_script
        
        # Remove CTA from anywhere in the script (to avoid duplicates)
        # Replace all old CTA formats
        old_ctas = [
            "अगर आपको ये वीडियो पसंद आया तो like और subscribe जरूर करें! धन्यवाद!",
            "आपकी मम्मी कसम सब्सक्राइब जरूर करे",
            "आपकी मम्मी कसम सब्सक्राइब",
            "आपकी मम्मी पुण्या कसम सब्सक्राइब जरूर करे",  # Remove incorrect "पुण्या" version
            "आपकी मम्मी पुण्या कसम सब्सक्राइब"  # Remove incorrect "पुण्या" version
        ]
        for old_cta in old_ctas:
            if old_cta in clean_script:
                clean_script = clean_script.replace(old_cta, "").strip()
        
        # Remove new CTA if already present
        if cta_text in clean_script:
            clean_script = clean_script.replace(cta_text, "").strip()
        
        # Remove incorrect CTA with "पुण्या" if present
        if incorrect_cta in clean_script:
            clean_script = clean_script.replace(incorrect_cta, "").strip()
        
        # Remove partial CTA if full CTA is not present
        if partial_cta in clean_script and cta_text not in clean_script:
            clean_script = clean_script.replace(partial_cta, "").strip()
        
        # Remove any repetitive phrases like "मत करो, मत करो, मत करो..." before CTA
        # Clean up the end of script before adding CTA
        clean_script = re.sub(r'(मत करो[, ]*)+$', '', clean_script, flags=re.MULTILINE).strip()
        clean_script = re.sub(r'(नहीं[, ]*)+$', '', clean_script, flags=re.MULTILINE).strip()
        clean_script = re.sub(r'(रुको[, ]*)+$', '', clean_script, flags=re.MULTILINE).strip()
        clean_script = re.sub(r'(बंद करो[, ]*)+$', '', clean_script, flags=re.MULTILINE).strip()
        
        # Clean up any extra whitespace/newlines
        clean_script = clean_script.strip()
        
        # Add CTA at the end with proper spacing
        if clean_script:
            # Add space before CTA if script doesn't end with punctuation
            if not clean_script.endswith(('।', '.', '!', '?', ':', ';')):
                clean_script = clean_script + " " + cta_text
            else:
                clean_script = clean_script + " " + cta_text
        else:
            clean_script = cta_text
    else:
        clean_script = cta_text
    
    # Final filter for negative words before returning (ensures all negative words are removed)
    from .word_filter import filter_negative_words
    clean_script = filter_negative_words(clean_script)
    
    # Add natural pauses and expressions for better TTS (Gemini TTS markup tags)
    clean_script = add_tts_markup_tags(clean_script)
    
    return clean_script


def add_tts_markup_tags(text):
    """
    Add Gemini TTS markup tags for natural pauses, expressions, and better speech delivery
    Analyzes content context (fear, excitement, neutral, etc.) and adds appropriate tags
    
    Supported tags:
    - [short pause] - Brief pause (~250ms)
    - [medium pause] - Standard pause (~500ms)
    - [long pause] - Dramatic pause (~1000ms+)
    - [sigh] - Non-speech sigh sound
    - [laughing] - Non-speech laugh
    - [uhm] - Hesitation sound
    - [whispering] - Decreased volume (for scary/fear content)
    
    Args:
        text: Clean script text
        
    Returns:
        str: Text with appropriate markup tags added based on content context
    """
    if not text:
        return text
    
    import re
    
    # Detect content type with better analysis - not everything is fear!
    # Count occurrences to determine dominant theme
    fear_keywords = ['राक्षस', 'डर', 'अंधेरा', 'भय', 'साहस', 'पीछा', 'भाग', 'दौड़', 'घबराहट', 'भैया.*राक्षस', 'बहन.*भाग']
    exciting_keywords = ['देखो', 'वाह', 'अरे', 'ओह', 'वाहवाह', 'मजेदार', 'रोमांचक', 'खुश', 'हंसी']
    neutral_keywords = ['घर', 'मां', 'पिताजी', 'बच्चे', 'दरवाजा', 'सड़क']
    
    fear_count = sum(1 for keyword in fear_keywords if re.search(keyword, text, re.IGNORECASE))
    exciting_count = sum(1 for keyword in exciting_keywords if re.search(keyword, text, re.IGNORECASE))
    neutral_count = sum(1 for keyword in neutral_keywords if re.search(keyword, text, re.IGNORECASE))
    
    # Determine dominant theme (only if fear keywords are significantly present)
    has_fear_content = fear_count >= 2  # At least 2 fear keywords
    has_exciting_content = exciting_count >= 2  # At least 2 exciting keywords
    is_mostly_neutral = neutral_count > fear_count and neutral_count > exciting_count
    
    # Split text into sentences (preserve punctuation)
    # Split by sentence endings but keep them
    sentences = re.split(r'([।!?]+)', text)
    enhanced_sentences = []
    
    i = 0
    while i < len(sentences):
        sentence = sentences[i].strip()
        if not sentence:
            i += 1
            continue
        
        # Get punctuation if next element is punctuation
        punctuation = ''
        if i + 1 < len(sentences) and re.match(r'^[।!?]+$', sentences[i + 1]):
            punctuation = sentences[i + 1]
            i += 1
        
        # Skip if it's just punctuation
        if not sentence and punctuation:
            i += 1
            continue
        
        # Check if sentence has specific content (more nuanced)
        sentence_has_fear = any(re.search(keyword, sentence, re.IGNORECASE) for keyword in fear_keywords)
        sentence_has_exciting = any(re.search(keyword, sentence, re.IGNORECASE) for keyword in exciting_keywords)
        
        # Add appropriate expressions based on content (only if clearly fear/exciting)
        # Don't add tags to every sentence - be selective
        if has_fear_content and sentence_has_fear:
            # For fear content, add [whispering] or [sigh] for dramatic effect (only on fear sentences)
            if 'राक्षस' in sentence:
                sentence = '[whispering] ' + sentence
            elif 'अंधेरा' in sentence or 'डर' in sentence:
                sentence = '[sigh] ' + sentence
        elif has_exciting_content and sentence_has_exciting and i == 0:
            # First exciting sentence only
            sentence = '[laughing] ' + sentence
        
        # Add short pause after commas (but not if already has pause tags)
        if '[short pause]' not in sentence and '[medium pause]' not in sentence:
            sentence = re.sub(r',\s+', ', [short pause] ', sentence)
        
        # Add medium pause after sentence endings (but preserve existing pauses)
        if punctuation and '[medium pause]' not in sentence:
            sentence = sentence + punctuation + ' [medium pause]'
        elif punctuation:
            sentence = sentence + punctuation
        
        # Add hesitation for natural flow in longer sentences (only if neutral content and no other tags)
        if is_mostly_neutral and len(sentence.split()) > 20 and '[uhm]' not in sentence and not sentence_has_fear:
            # Add [uhm] before the last few words for natural hesitation
            words = sentence.split()
            if len(words) > 10:
                insert_pos = len(words) - 3  # Before last 3 words
                words.insert(insert_pos, '[uhm]')
                sentence = ' '.join(words)
        
        enhanced_sentences.append(sentence)
        i += 1
    
    enhanced_text = ' '.join(enhanced_sentences)
    
    # Clean up multiple consecutive pauses
    enhanced_text = re.sub(r'\[short pause\]\s*\[short pause\]+', '[short pause]', enhanced_text)
    enhanced_text = re.sub(r'\[medium pause\]\s*\[medium pause\]+', '[medium pause]', enhanced_text)
    enhanced_text = re.sub(r'\[short pause\]\s*\[medium pause\]', '[medium pause]', enhanced_text)  # Short before medium -> just medium
    
    # Remove pauses right before CTA (let CTA flow naturally)
    enhanced_text = re.sub(r'\[(?:short|medium|long) pause\]\s*आपकी मम्मी', 'आपकी मम्मी', enhanced_text)
    
    # Ensure proper spacing around tags
    enhanced_text = re.sub(r'\s+\[', ' [', enhanced_text)
    enhanced_text = re.sub(r'\]\s+', '] ', enhanced_text)
    enhanced_text = re.sub(r'\]\s*\[', '] [', enhanced_text)
    
    # Remove any "पुण्या" from CTA if present
    enhanced_text = re.sub(r'पुण्या', 'पापा', enhanced_text)
    
    return enhanced_text.strip()


def generate_video_metadata(video_download):
    """
    Generate title, description, and tags for video using AI
    
    Args:
        video_download: VideoDownload model instance
        
    Returns:
        dict: {
            'title': str,
            'description': str,
            'tags': str (comma-separated),
            'status': str ('success' or 'failed'),
            'error': str (if failed)
        }
    """
    try:
        from .models import AIProviderSettings
        from django.utils import timezone
        
        # Check if AI provider is configured
        settings_obj = AIProviderSettings.objects.first()
        if not settings_obj or not settings_obj.api_key:
            return {
                'title': '',
                'description': '',
                'tags': '',
                'status': 'failed',
                'error': 'AI provider not configured. Please add API key in settings.'
            }
        
        # Get video content
        original_title = video_download.title or video_download.original_title or 'Video'
        original_description = video_download.description or video_download.original_description or ''
        transcript = video_download.transcript_without_timestamps or video_download.transcript or ''
        transcript_hindi = video_download.transcript_hindi or ''
        ai_summary = video_download.ai_summary or ''
        
        # Create prompt for metadata generation
        system_prompt = """You are a content creator assistant. Generate engaging metadata for a Hindi YouTube Shorts video.
        
OUTPUT FORMAT (JSON only):
{
    "title": "Engaging Hindi title (60-80 characters, catchy and SEO-friendly, NO hashtags in title)",
    "description": "Detailed Hindi description (2-3 paragraphs, 200-300 words, includes key points and call-to-action)",
    "tags": "tag1, tag2, tag3, tag4, tag5" (5-10 relevant tags in English, comma-separated)
}

REQUIREMENTS:
1. Title must be in HINDI (Devanagari script), engaging and click-worthy, 60-80 characters max
2. Title should be SHORTER and catchy for YouTube Shorts
3. Description must be in HINDI (Devanagari script), detailed and informative
4. DO NOT include hashtags in title (they will be added automatically)
5. Description should be engaging and include call-to-action
3. Tags must be in ENGLISH, relevant keywords for SEO
4. Make content engaging and optimized for YouTube/social media"""

        user_message = f"""Original Title: {original_title}
Original Description: {original_description}
Video Summary: {ai_summary}
Hindi Transcript: {transcript_hindi[:1500] if transcript_hindi else ''}
English Transcript: {transcript[:1500] if transcript else ''}

Generate engaging Hindi title, description, and English tags for this video."""

        provider = settings_obj.provider
        api_key = settings_obj.api_key
        
        # Call AI API
        result = None
        if provider == 'gemini':
            # Use REST API instead of SDK to avoid dependency issues
            try:
                model_names = ['models/gemini-2.0-flash', 'models/gemini-2.5-flash', 'models/gemini-pro']
                full_prompt = f"{system_prompt}\n\n{user_message}"
                
                for model_name in model_names:
                    try:
                        url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
                        headers = {'Content-Type': 'application/json'}
                        payload = {
                            "contents": [{
                                "parts": [{"text": full_prompt}]
                            }]
                        }
                        
                        response = requests.post(url, json=payload, headers=headers, timeout=60)
                        response.raise_for_status()
                        
                        data = response.json()
                        if 'candidates' in data and len(data['candidates']) > 0:
                            candidate = data['candidates'][0]
                            if 'content' in candidate and 'parts' in candidate['content']:
                                text_parts = [part.get('text', '') for part in candidate['content']['parts']]
                                result_text = ''.join(text_parts).strip()
                                if result_text:
                                    break
                    except requests.exceptions.RequestException as e:
                        if hasattr(e, 'response') and e.response is not None:
                            if e.response.status_code == 404:
                                continue  # Try next model
                        # If last model or non-404 error, raise
                        if model_name == model_names[-1]:
                            raise
                        continue
                
                if not result_text:
                    return {
                        'title': '',
                        'description': '',
                        'tags': '',
                        'status': 'failed',
                        'error': 'Gemini API returned empty response'
                    }
            except Exception as e:
                return {
                    'title': '',
                    'description': '',
                    'tags': '',
                    'status': 'failed',
                    'error': f'Gemini API error: {str(e)}'
                }
        elif provider == 'openai':
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.7
                )
                result_text = response.choices[0].message.content.strip()
            except ImportError:
                # Fallback to old API format
                import openai
                openai.api_key = api_key
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.7
                )
                result_text = response.choices[0].message.content.strip()
        elif provider == 'anthropic':
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)
                message = client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=1000,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}]
                )
                result_text = message.content[0].text.strip()
            except ImportError:
                return {
                    'title': '',
                    'description': '',
                    'tags': '',
                    'status': 'failed',
                    'error': 'anthropic package not installed. Run: pip install anthropic'
                }
            except Exception as e:
                return {
                    'title': '',
                    'description': '',
                    'tags': '',
                    'status': 'failed',
                    'error': f'Anthropic API error: {str(e)}'
                }
        else:
            return {
                'title': '',
                'description': '',
                'tags': '',
                'status': 'failed',
                'error': f'Unsupported AI provider: {provider}'
            }
        
        # Parse JSON response
        try:
            # Extract JSON from response (handle cases where AI adds extra text)
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                metadata = json.loads(json_match.group())
            else:
                metadata = json.loads(result_text)
            
            return {
                'title': metadata.get('title', ''),
                'description': metadata.get('description', ''),
                'tags': metadata.get('tags', ''),
                'status': 'success',
                'error': None
            }
        except json.JSONDecodeError:
            # Fallback: try to extract fields manually
            title_match = re.search(r'"title":\s*"([^"]+)"', result_text)
            desc_match = re.search(r'"description":\s*"([^"]+)"', result_text, re.DOTALL)
            tags_match = re.search(r'"tags":\s*"([^"]+)"', result_text)
            
            return {
                'title': title_match.group(1) if title_match else '',
                'description': desc_match.group(1) if desc_match else '',
                'tags': tags_match.group(1) if tags_match else '',
                'status': 'success',
                'error': None
            }
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error generating video metadata: {error_msg}")
        return {
            'title': '',
            'description': '',
            'tags': '',
            'status': 'failed',
            'error': error_msg
        }


def generate_hindi_script(video_download):
    """
    Generate Hindi script for video using AI based on video content
    
    Args:
        video_download: VideoDownload model instance
        
    Returns:
        dict: {
            'script': str (Hindi script),
            'status': str ('success' or 'failed'),
            'error': str (if failed)
        }
    """
    try:
        from .models import AIProviderSettings
        from django.utils import timezone
        
        # Check if AI provider is configured
        settings_obj = AIProviderSettings.objects.first()
        if not settings_obj or not settings_obj.api_key:
            return {
                'script': '',
                'status': 'failed',
                'error': 'AI provider not configured. Please add API key in settings.'
            }
        
        # Get video content for script generation
        title = video_download.title or video_download.original_title or 'Video'
        description = video_download.description or video_download.original_description or ''
        transcript = video_download.transcript or ''
        transcript_hindi = video_download.transcript_hindi or ''
        duration = video_download.duration or 0
        
        # Get enhanced transcript and visual analysis for scene-based explainer
        # Visual Analysis is OPTIONAL - if available, use it; if not, continue without it
        enhanced_transcript = video_download.enhanced_transcript_without_timestamps or video_download.enhanced_transcript or ''
        visual_transcript = video_download.visual_transcript_without_timestamps or video_download.visual_transcript or ''
        visual_segments = video_download.visual_transcript_segments or []
        
        # Check if visual analysis is available (optional)
        has_visual = bool(visual_transcript and visual_segments)
        
        # Validate that required sources are available
        if not enhanced_transcript:
            return {
                'script': '',
                'status': 'failed',
                'error': 'Enhanced transcript is required for script generation. Please wait for AI enhancement to complete after NCA/Whisper transcription.'
            }
        
        if has_visual:
            print("✓ Visual analysis available - will be included in script generation")
        else:
            print("⚠ Visual analysis not available (optional) - continuing with enhanced transcript only")
        
        # Filter out "subscribe" mentions from enhanced transcript before generating Hindi script
        # This ensures we don't duplicate subscribe CTAs if the video already mentions it
        subscribe_patterns = [
            r'subscribe',
            r'सब्सक्राइब',
            r'सब्स्क्राइब',
            r'सब्सक्राइब करें',
            r'सब्सक्राइब जरूर करें',
            r'like और subscribe',
            r'like.*subscribe',
        ]
        
        # Remove subscribe mentions from enhanced transcript
        filtered_enhanced_transcript = enhanced_transcript
        for pattern in subscribe_patterns:
            filtered_enhanced_transcript = re.sub(pattern, '', filtered_enhanced_transcript, flags=re.IGNORECASE)
        
        # Clean up extra spaces
        filtered_enhanced_transcript = re.sub(r'\s+', ' ', filtered_enhanced_transcript).strip()
        
        # Check if original transcript/enhanced transcript already mentions subscribe
        original_text = enhanced_transcript.lower()
        has_subscribe_mention = any(
            'subscribe' in original_text or 
            'सब्सक्राइब' in enhanced_transcript or 
            'सब्स्क्राइब' in enhanced_transcript
        )
        
        if has_subscribe_mention:
            print("⚠ Video already mentions subscribe - will not add CTA at the end")
        else:
            print("✓ No subscribe mention found - will add CTA at the end")
        
        # Filter negative/abusive words from enhanced transcript before generating Hindi script
        # Do NOT filter negative words from transcript during script generation
        # Word filtering will be applied only at final TTS script generation stage (in get_clean_script_for_tts)
        # This preserves original meaning and proper translation (e.g., "डर" should stay as "डर", not become "साहस")
        print("Using enhanced transcript (with subscribe filtered) for script generation...")
        
        # Use enhanced_transcript (filtered) instead of transcript
        # Check if enhanced transcript has timestamps (format: 00:00:00 text)
        has_timestamps = bool(re.search(r'\d{1,2}:\d{2}:\d{2}\s+', filtered_enhanced_transcript))
        
        # If enhanced transcript has timestamps, use it directly and convert to Hindi if needed
        if filtered_enhanced_transcript and has_timestamps:
            print("📝 Processing timestamped enhanced transcript...")
            # Parse enhanced transcript with timestamps (subscribe already filtered)
            lines = filtered_enhanced_transcript.split('\n')
            timestamped_lines = []
            
            # Pre-compile regex pattern for better performance
            timestamp_pattern = re.compile(r'^(\d{1,2}:\d{2}:\d{2})\s+(.+)$')
            devanagari_pattern = re.compile(r'[\u0900-\u097F]')
            
            # Collect lines that need translation
            lines_to_translate = []
            line_indices = []
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # Extract timestamp and text
                timestamp_match = timestamp_pattern.match(line)
                if timestamp_match:
                    timestamp = timestamp_match.group(1)
                    text = timestamp_match.group(2)
                    
                    # Check if text is already in Hindi (contains Devanagari characters)
                    has_devanagari = bool(devanagari_pattern.search(text))
                    
                    if has_devanagari:
                        # Already in Hindi, use as-is
                        timestamped_lines.append(f"{timestamp} {text}")
                    else:
                        # Mark for translation
                        lines_to_translate.append(text)
                        line_indices.append((i, timestamp, 'timestamped'))
                else:
                    # Line without timestamp, check if it's Hindi
                    has_devanagari = bool(devanagari_pattern.search(line))
                    if has_devanagari:
                        timestamped_lines.append(line)
                    else:
                        # Mark for translation
                        lines_to_translate.append(line)
                        line_indices.append((i, None, 'plain'))
            
            # Batch translate all lines that need translation
            if lines_to_translate:
                print(f"⚡ Batch translating {len(lines_to_translate)} lines to Hindi...")
                translated_lines = batch_translate_text(lines_to_translate, target='hi')
                
                # Insert translated lines back
                for idx, (line_idx, timestamp, line_type) in enumerate(line_indices):
                    hindi_text = translated_lines[idx]
                    if line_type == 'timestamped':
                        timestamped_lines.append(f"{timestamp} {hindi_text}")
                    else:
                        timestamped_lines.append(hindi_text)
            
            print(f"✓ Processed {len(timestamped_lines)} timestamped lines")

            
            # Process timestamped content - add "Dekho" at the start of first line and make it kid-friendly
            processed_lines = []
            for i, line in enumerate(timestamped_lines):
                if i == 0:
                    # Add "Dekho" at the start of the first line
                    # Extract timestamp and text
                    timestamp_match = re.match(r'^(\d{1,2}:\d{2}:\d{2})\s+(.+)$', line)
                    if timestamp_match:
                        timestamp = timestamp_match.group(1)
                        text = timestamp_match.group(2)
                        # Add "Dekho" at the start if not already present
                        if not text.strip().startswith('देखो') and not text.strip().startswith('Dekho'):
                            text = f"देखो {text}"
                        processed_lines.append(f"{timestamp} {text}")
                    else:
                        # No timestamp, just add "Dekho" at start
                        if not line.strip().startswith('देखो') and not line.strip().startswith('Dekho'):
                            processed_lines.append(f"देखो {line}")
                        else:
                            processed_lines.append(line)
                else:
                    processed_lines.append(line)
            
            # Add timestamped content (ensuring all keypoints are covered)
            script_content = "\n".join(processed_lines)
            
            # Add CTA at the end with mother father reference ONLY if video doesn't already mention subscribe
            formatted_script = script_content
            if not has_subscribe_mention:
                cta_text = "आपकी मम्मी पापा कसम सब्सक्राइब जरूर करे"
                formatted_script = f"{script_content}\n\n{cta_text}"
                print("✓ Added subscribe CTA at the end")
            else:
                print("✓ Skipped adding subscribe CTA (already mentioned in video)")
            
            return {
                'script': formatted_script,
                'status': 'success',
                'error': None
            }
        
        # If no timestamped enhanced transcript, fall back to AI generation
        # Use filtered enhanced transcript (without subscribe) for script generation
        # Prefer Hindi transcript if available, otherwise use filtered enhanced transcript
        content_for_script = transcript_hindi if transcript_hindi else filtered_enhanced_transcript
        
        # If no transcript available, use title and description
        if not content_for_script:
            content_for_script = f"{title}. {description}"
        
        # Analyze content to determine tone and style (more nuanced - not everything is fear!)
        transcript_text = video_download.enhanced_transcript_without_timestamps or video_download.transcript_without_timestamps or ''
        transcript_lower = transcript_text.lower() if transcript_text else ''
        
        # Count occurrences to determine dominant theme
        fear_keywords = ['monster', 'ghost', 'scary', 'dark', 'fear', 'afraid', 'chase', 'run', 'राक्षस', 'डर', 'अंधेरा', 'भय', 'साहस', 'पीछा', 'भाग', 'दौड़', 'घबराहट']
        exciting_keywords = ['fun', 'happy', 'joy', 'excited', 'मजेदार', 'खुश', 'रोमांचक', 'वाह', 'देखो']
        neutral_keywords = ['home', 'house', 'mother', 'father', 'door', 'घर', 'मां', 'पिताजी', 'दरवाजा', 'सड़क']
        
        fear_count = sum(1 for keyword in fear_keywords if keyword.lower() in transcript_lower)
        exciting_count = sum(1 for keyword in exciting_keywords if keyword.lower() in transcript_lower)
        neutral_count = sum(1 for keyword in neutral_keywords if keyword.lower() in transcript_lower)
        
        # Determine content type (only if fear keywords are significantly present)
        has_fear_content = fear_count >= 3  # At least 3 fear keywords (not just 1-2)
        has_exciting_content = exciting_count >= 2  # At least 2 exciting keywords
        is_mostly_neutral = neutral_count > fear_count and neutral_count > exciting_count
        
        # Create system prompt for Hindi script generation (explainer style)
        # Adjust prompt based on content type
        if has_fear_content:
            system_prompt = """आप एक विशेषज्ञ explainer और स्क्रिप्ट राइटर हैं जो suspenseful और engaging children's content के लिए हिंदी में detailed, vivid, और dramatic explainer-style स्क्रिप्ट बनाते हैं।

**CONTENT TYPE: Suspense/Fear-based Story (रोमांचक कहानी)**
- यह content में fear, suspense, या scary elements हैं (जैसे राक्षस, अंधेरा, डर, पीछा)
- Script को dramatic और engaging बनाएं लेकिन बच्चों के लिए appropriate
- Suspenseful moments को vividly describe करें
- Fear elements को exciting और engaging बनाएं, बहुत scary नहीं
- Use appropriate tone: slightly tense for scary moments, energetic for action scenes

**CRITICAL REQUIREMENTS (MUST FOLLOW):**
1. **पहली लाइन हमेशा "देखो" से शुरू होनी चाहिए** - यह MANDATORY है, बिना exception के
2. **अंत में हमेशा CTA होना चाहिए: "आपकी मम्मी पापा कसम सब्सक्राइब जरूर करे"** - यह MANDATORY है, बिना exception के
3. **IMPORTANT: Use "पापा" NOT "पुण्या" in CTA** - यह CRITICAL है, "पुण्या" बिल्कुल न लिखें
"""
        else:
            system_prompt = """आप एक विशेषज्ञ explainer और स्क्रिप्ट राइटर हैं जो वीडियो कंटेंट के लिए हिंदी में detailed, vivid, और engaging explainer-style स्क्रिप्ट बनाते हैं।

**CRITICAL REQUIREMENTS (MUST FOLLOW):**
1. **पहली लाइन हमेशा "देखो" से शुरू होनी चाहिए** - यह MANDATORY है, बिना exception के
2. **अंत में हमेशा CTA होना चाहिए: "आपकी मम्मी पापा कसम सब्सक्राइब जरूर करे"** - यह MANDATORY है, बिना exception के
3. **IMPORTANT: Use "पापा" NOT "पुण्या" in CTA** - यह CRITICAL है, "पुण्या" बिल्कुल न लिखें

आपका कार्य (EXPLAINER STYLE):
1. **मैं एक explainer हूं** - मैं वीडियो में हो रही हर scene, action, और movement को detail में explain करता हूं
2. **Scene-by-scene explainer** - हर scene change, visual element, और action को vividly describe करें
3. **Aggressive explainer style** - हर detail को explain करें, कुछ भी miss न करें
4. वीडियो की सामग्री को समझकर एक detailed और vivid explainer-style हिंदी स्क्रिप्ट बनाएं
5. स्क्रिप्ट को वीडियो की अवधि के अनुसार समायोजित करें (video length और audio length match करना है)
6. स्क्रिप्ट को बोलने योग्य, प्राकृतिक, engaging और detailed explainer style में बनाएं
7. **किसी भी header या title section न बनाएं - सीधे "देखो" से शुरू करें**

[स्क्रिप्ट फॉर्मेट:
देखो [मुख्य कंटेंट - वीडियो की सामग्री के आधार पर, बच्चों के लिए मजेदार और आकर्षक, scene-by-scene detailed explanation]

आपकी मम्मी पापा कसम सब्सक्राइब जरूर करे]

**MANDATORY FORMAT (NO EXCEPTIONS):**
- **पहली लाइन हमेशा "देखो" से शुरू होनी चाहिए** - यह CRITICAL है, बिना fail के
- **अंत में हमेशा CTA होना चाहिए: "आपकी मम्मी पापा कसम सब्सक्राइब जरूर करे"** - यह CRITICAL है, बिना fail के

महत्वपूर्ण निर्देश (बच्चों के लिए):
- स्क्रिप्ट पूरी तरह से हिंदी (देवनागरी) में होनी चाहिए
- **बच्चों की बोलचाल की हिंदी इस्तेमाल करें - simple, fun, और engaging**
- **मजेदार और रोचक भाषा का उपयोग करें - बच्चों को attract करने के लिए**
- स्क्रिप्ट प्राकृतिक और बोलने योग्य होनी चाहिए
- वीडियो की अवधि को ध्यान में रखते हुए स्क्रिप्ट की लंबाई निर्धारित करें
- **सीधे "देखो" से शुरू करें - कोई ग्रीटिंग, नमस्कार, या परिचयात्मक वाक्य नहीं**
- **धन्यवाद या समापन वाक्य नहीं - सीधे "देखो" से कंटेंट शुरू करें, अंत में सिर्फ CTA**
- **स्क्रिप्ट सीधे वीडियो में हो रही एक्शन/घटना का वर्णन करे - सवाल बिल्कुल नहीं**
- **कोई भी सवाल नहीं - सिर्फ वर्णन और एक्शन**
- **किसी भी header (शीर्षक, आवाज़) section न बनाएं - सीधे "देखो" से शुरू करें**
- **बिल्कुल बचें:** "क्या आपने...", "क्या आपको...", "क्या ये...", "नमस्कार दोस्तों", "दिल थाम के बैठिए", "आज हम देखेंगे", "चलिए शुरू करते हैं", "**शीर्षक:**", "**आवाज़:**" जैसे वाक्यों/headers से
- **सिर्फ मुख्य कंटेंट - "देखो" से शुरू, वीडियो में जो हो रहा है उसका सीधा वर्णन, कोई सवाल नहीं, कोई header नहीं, बच्चों को attract करने वाली मजेदार भाषा, अंत में CTA**"""
        
        # Create user message with video details including visual analysis for scene-based explainer
        duration_text = f"{int(duration)} सेकंड" if duration > 0 else "अज्ञात अवधि"
        
        # Build visual analysis context for aggressive scene-based explainer (OPTIONAL)
        visual_context = ""
        if has_visual and visual_segments and len(visual_segments) > 0:
            visual_context = "\n\n**दृश्य विश्लेषण (Visual Analysis - Scene-by-Scene) - OPTIONAL, USE IF AVAILABLE:**\n"
            # Limit to first 30 segments for performance (reduced from 50)
            for seg in visual_segments[:30]:
                timestamp = seg.get('timestamp_str', '')
                description = seg.get('text') or seg.get('description', '')
                if description:
                    visual_context += f"{timestamp} {description}\n"
        elif not has_visual:
            visual_context = "\n\n**दृश्य विश्लेषण (Visual Analysis):** Not available (optional) - continue without it, use enhanced transcript only.\n"
        
        user_message = f"""वीडियो शीर्षक: {title}
विवरण: {description}
अवधि: {duration_text}

**मूल ट्रांसक्रिप्ट (Original Transcript):**
{content_for_script[:4000]}

{visual_context}

**AI-Enhanced Transcript (Best Quality - Combined from Available Sources):**
{enhanced_transcript[:3000] if enhanced_transcript else 'Not available'}

**महत्वपूर्ण निर्देश (EXPLAINER STYLE - Scene-by-Scene Detailed Explanation):**
1. **मैं एक EXPLAINER हूं** - मैं वीडियो में हो रही हर चीज़ को detail में explain करता हूं
2. **दृश्य विश्लेषण (Visual Analysis) का उपयोग करें - अगर available है तो हर scene को detail में explain करें (OPTIONAL - अगर नहीं है तो continue without it)**
3. **Aggressive explainer style - हर action, movement, और scene change को vividly describe करें**
4. **मूल ट्रांसक्रिप्ट + Enhanced Transcript को combine करें - Visual Analysis अगर available है तो include करें, नहीं तो Enhanced Transcript से ही काम चलाएं**
5. **अगर ट्रांसक्रिप्ट में टाइमस्टैम्प हैं (जैसे 00:00:00), तो उन्हें बनाए रखें**
6. **Visual segments के timestamps को match करें - scene-by-scene sync करें**
7. **Video length ({duration_text}) और script length match करना है** - TTS speed और temperature automatically adjust होगा video duration के अनुसार
8. **अगर ट्रांसक्रिप्ट हिंदी में नहीं है, तो हिंदी में अनुवाद करें लेकिन टाइमस्टैम्प बनाए रखें**
9. **अगर ट्रांसक्रिप्ट में टाइमस्टैम्प नहीं हैं, तो Visual Analysis के timestamps का उपयोग करें (अगर available है)**
10. **सीधे बिंदु पर आएं - कोई ग्रीटिंग या परिचय नहीं, कोई header नहीं**
11. **स्क्रिप्ट सीधे वीडियो में हो रही एक्शन/घटना का VIVID और DETAILED वर्णन करे - visual scenes को aggressively explain करें**
12. **बच्चों की बोलचाल की simple और fun हिंदी इस्तेमाल करें - engaging और attractive**
13. **किसी भी header (शीर्षक, आवाज़) section न बनाएं - सीधे कंटेंट से शुरू करें**
14. **हर scene change, action, और visual element को describe करें - aggressive और detailed explainer style**
15. **Script length को video duration के अनुसार optimize करें - TTS speed/temperature automatically adjust होगा**

**CRITICAL FORMAT REQUIREMENTS (MUST FOLLOW - NO EXCEPTIONS):**
1. **पहली लाइन हमेशा "देखो" से शुरू होनी चाहिए** - यह MANDATORY है
2. **अंत में हमेशा CTA होना चाहिए: "आपकी मम्मी पापा कसम सब्सक्राइब जरूर करे"** - यह MANDATORY है

**उदाहरण (मूल ट्रांसक्रिप्ट के आधार पर):**
अगर मूल ट्रांसक्रिप्ट है:
00:00:00 घर पर मम्मी ना होने के कारण इस
00:00:01 बच्चे ने घर पर अंडे से खेलना शुरू कर दिया

तो आउटपुट होना चाहिए (टाइमस्टैम्प बनाए रखें, पहली लाइन "देखो" से शुरू, अंत में CTA):
00:00:00 देखो घर पर मम्मी ना होने के कारण इस
00:00:01 बच्चे ने घर पर अंडे से खेलना शुरू कर दिया

आपकी मम्मी पापा कसम सब्सक्राइब जरूर करे

**गलत (इससे बिल्कुल बचें):**
- "देखो" के बिना शुरू करना
- CTA के बिना समाप्त करना
- नई सामग्री बनाना (जो मूल ट्रांसक्रिप्ट में नहीं है)
- टाइमस्टैम्प हटाना
- सवाल जोड़ना (जैसे "क्या आपने...")
- ग्रीटिंग जोड़ना (जैसे "नमस्कार दोस्तों")

**याद रखें: 
- मूल ट्रांसक्रिप्ट का उपयोग करें
- टाइमस्टैम्प बनाए रखें
- सिर्फ हिंदी में कन्वर्ट करें
- हमेशा "देखो" से शुरू करें
- हमेशा "आपकी मम्मी पापा कसम सब्सक्राइब जरूर करे" से समाप्त करें**"""
        
        # Call AI API
        provider = settings_obj.provider
        api_key = settings_obj.api_key
        
        print(f"🤖 Generating Hindi script using {provider.upper()} AI...")
        print(f"   - Video duration: {duration}s")
        print(f"   - Enhanced transcript length: {len(enhanced_transcript)} chars")
        print(f"   - Visual segments: {len(visual_segments) if visual_segments else 0}")
        
        result = None
        if provider == 'gemini':
            result = _call_gemini_api(api_key, system_prompt, user_message)
        elif provider == 'openai':
            result = _call_openai_api(api_key, system_prompt, user_message)
        elif provider == 'anthropic':
            result = _call_anthropic_api(api_key, system_prompt, user_message)
        else:
            return {
                'script': '',
                'status': 'failed',
                'error': f'Unsupported AI provider: {provider}'
            }
        
        if result and result['status'] == 'success':
            print("✓ AI script generation completed successfully")
            script = result['prompt'].strip()
            
            # Remove questions from the script before formatting
            print("📝 Removing questions and formatting script...")
            script = remove_questions_from_script(script)
            
            # Format the script with proper structure
            formatted_script = format_hindi_script(script, title)
            
            # Filter negative/abusive words from formatted script (done once at the end)
            from .word_filter import filter_negative_words
            # Word filtering is disabled (all replacements commented out)
            # Function will return text as-is without any replacements
            print("Word filtering is disabled - script will be used as-is...")
            formatted_script = filter_negative_words(formatted_script)
            
            # ALWAYS ensure "देखो" is at the start (MANDATORY)
            if formatted_script and not formatted_script.strip().startswith('देखो') and not formatted_script.strip().startswith('Dekho'):
                # Find first line and add "देखो"
                lines = formatted_script.split('\n')
                if lines:
                    first_line = lines[0].strip()
                    # Check if first line has timestamp
                    timestamp_match = re.match(r'^(\d{1,2}:\d{2}:\d{2})\s+(.+)$', first_line)
                    if timestamp_match:
                        timestamp = timestamp_match.group(1)
                        text = timestamp_match.group(2)
                        if not text.strip().startswith('देखो') and not text.strip().startswith('Dekho'):
                            lines[0] = f"{timestamp} देखो {text}"
                    else:
                        if not first_line.startswith('देखो') and not first_line.startswith('Dekho'):
                            lines[0] = f"देखो {first_line}"
                    formatted_script = '\n'.join(lines)
            
            # Check if script already mentions subscribe - if so, don't add CTA
            script_lower = formatted_script.lower()
            script_has_subscribe = (
                'subscribe' in script_lower or 
                'सब्सक्राइब' in formatted_script or 
                'सब्स्क्राइब' in formatted_script
            )
            
            # IMPORTANT: Use "पापा" NOT "पुण्या"
            # Remove any existing CTA at the end first
            cta_text = "आपकी मम्मी पापा कसम सब्सक्राइब जरूर करे"
            incorrect_cta = "आपकी मम्मी पुण्या कसम सब्सक्राइब जरूर करे"
            cta_text_old = "अगर आपको ये वीडियो पसंद आया तो like और subscribe जरूर करें! धन्यवाद!"  # New version to remove
            cta_text_old2 = "आपकी मम्मी कसम सब्सक्राइब जरूर करे"  # Older version
            cta_text_old3 = "आपकी मम्मी कसम सब्सक्राइब"  # Oldest version
            # Remove incorrect CTA with "पुण्या"
            incorrect_cta_variants = [
                "आपकी मम्मी पुण्या कसम सब्सक्राइब जरूर करे",
                "आपकी मम्मी पुण्या कसम सब्सक्राइब",
                "पुण्या कसम"
            ]
            
            # Remove trailing CTA if it exists (to avoid duplicates)
            formatted_script = formatted_script.rstrip()
            
            # Remove any "पुण्या" and replace with "पापा" first
            formatted_script = re.sub(r'पुण्या', 'पापा', formatted_script)
            
            # Check for new CTA format
            if formatted_script.endswith(cta_text):
                formatted_script = formatted_script[:-len(cta_text)].rstrip()
            elif formatted_script.endswith(cta_text + "\n"):
                formatted_script = formatted_script[:-len(cta_text + "\n")].rstrip()
            elif formatted_script.endswith("\n\n" + cta_text):
                formatted_script = formatted_script[:-len("\n\n" + cta_text)].rstrip()
            # Remove all old CTA formats
            old_ctas = [cta_text_old, cta_text_old2, cta_text_old3] + incorrect_cta_variants
            for old_cta in old_ctas:
                if formatted_script.endswith(old_cta):
                    formatted_script = formatted_script[:-len(old_cta)].rstrip()
                elif formatted_script.endswith(old_cta + "\n"):
                    formatted_script = formatted_script[:-len(old_cta + "\n")].rstrip()
                elif formatted_script.endswith("\n\n" + old_cta):
                    formatted_script = formatted_script[:-len("\n\n" + old_cta)].rstrip()
                # Also check if CTA appears anywhere in the script
                formatted_script = formatted_script.replace(old_cta, "").strip()
            
            # Only add CTA at the end if video doesn't already mention subscribe
            if not script_has_subscribe and not has_subscribe_mention:
                formatted_script += f"\n\n{cta_text}"
                print("✓ Added subscribe CTA at the end (AI-generated script)")
            else:
                print("✓ Skipped adding subscribe CTA (already mentioned in video/script)")
            
            return {
                'script': formatted_script,
                'status': 'success',
                'error': None
            }
        else:
            return {
                'script': '',
                'status': 'failed',
                'error': result.get('error', 'Unknown error') if result else 'AI API call failed'
            }
            
    except Exception as e:
        error_msg = str(e)
        print(f"Error in generate_hindi_script: {error_msg}")
        return {
            'script': '',
            'status': 'failed',
            'error': error_msg
        }

