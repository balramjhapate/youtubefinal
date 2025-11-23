import re
import os
import json
import requests
import subprocess
import tempfile
from urllib.parse import urlparse
from pathlib import Path
from django.core.files.base import ContentFile
from django.conf import settings
from deep_translator import GoogleTranslator
from .nca_toolkit_client import get_nca_client

def extract_video_id(url):
    """Extract unique video ID from XHS URL"""
    # Try to find the ID in the URL path
    path = urlparse(url).path
    match = re.search(r'/item/([a-zA-Z0-9]+)', path)
    if match:
        return match.group(1)
    
    # If it's a short link or different format, we might need to resolve it first
    # But for now, let's assume standard format or use the full URL hash as fallback
    return None

def translate_text(text, target='en'):
    """Translate text to target language"""
    if not text:
        return ""
    try:
        return GoogleTranslator(source='auto', target=target).translate(text)
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def perform_extraction(url):
    """Perform video extraction using multiple methods"""
    # Priority 1: Try Seekin.ai API (Works on blocked IPs)
    print(f"Attempting extraction via Seekin.ai API: {url}")
    video_data = extract_video_seekin(url)
    if video_data:
        video_data['method'] = 'seekin'
        return video_data

    # Priority 2: yt-dlp (Works on local/unblocked IPs)
    print(f"Seekin API failed. Fallback to yt-dlp: {url}")
    video_data = extract_video_ytdlp(url)
    if video_data:
        video_data['method'] = 'yt-dlp'
        return video_data
    
    # Priority 3: Direct requests
    print(f"yt-dlp failed. Fallback to requests: {url}")
    video_data = extract_video_requests(url)
    if video_data:
        video_data['method'] = 'requests'
        return video_data
    
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

def extract_video_ytdlp(url):
    """Extract video using yt-dlp"""
    try:
        # Use the local yt-dlp binary
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        yt_dlp_path = os.path.join(base_dir, 'yt-dlp')
        
        if not os.path.exists(yt_dlp_path):
            yt_dlp_path = 'yt-dlp'

        result = subprocess.run(
            [yt_dlp_path, '--dump-json', url],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        
        video_url = data.get('url')
        if not video_url:
            formats = data.get('formats', [])
            if formats:
                best_video = sorted(formats, key=lambda x: x.get('height', 0), reverse=True)[0]
                video_url = best_video.get('url')

        if video_url:
            title = data.get('title', 'Xiaohongshu Video')
            description = data.get('description', '')
            return {
                "video_url": video_url,
                "title": title,
                "cover_url": data.get('thumbnail'),
                "original_title": title,
                "original_description": description
            }
        
        return None
    except Exception as e:
        print(f"yt-dlp extraction failed: {e}")
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
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        return ContentFile(response.content)
    except Exception as e:
        print(f"Download error: {e}")
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
                'summary': 'No content available for AI processing.',
                'tags': [],
                'transcript': '',
                'transcript_language': '',
                'status': 'failed',
                'error': 'No title, description, or transcript available'
            }
        
        # Step 3: Generate summary
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
        
        # Step 4: Generate tags based on transcript and metadata
        tags = []
        
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
        if output_audio_path is None:
            # Create temporary audio file
            temp_dir = tempfile.gettempdir()
            output_audio_path = os.path.join(temp_dir, f"audio_{os.path.basename(video_path)}.wav")
        
        # Use ffmpeg to extract audio (convert to WAV format for Whisper)
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # PCM 16-bit
            '-ar', '16000',  # Sample rate 16kHz (good for Whisper)
            '-ac', '1',  # Mono channel
            '-y',  # Overwrite output file
            output_audio_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            print(f"FFmpeg error: {result.stderr}")
            return None
        
        if os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 0:
            return output_audio_path
        else:
            print("Audio file was not created or is empty")
            return None
            
    except subprocess.TimeoutExpired:
        print("FFmpeg extraction timed out")
        return None
    except Exception as e:
        print(f"Error extracting audio: {e}")
        return None

def transcribe_audio_local(audio_path, language=None, model_size='base'):
    """
    Transcribe audio file locally using OpenAI Whisper
    
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
            'status': 'success' or 'failed',
            'error': str (if failed)
        }
    """
    try:
        # Import whisper (lazy import to avoid errors if not installed)
        try:
            import whisper
        except ImportError:
            return {
                'text': '',
                'language': '',
                'status': 'failed',
                'error': 'Whisper library not installed. Please install: pip install openai-whisper'
            }
        
        if not os.path.exists(audio_path):
            return {
                'text': '',
                'language': '',
                'status': 'failed',
                'error': f'Audio file not found: {audio_path}'
            }
        
        print(f"Loading Whisper model: {model_size}")
        # Load Whisper model (will download on first use)
        model = whisper.load_model(model_size)
        
        print(f"Transcribing audio: {audio_path}")
        # Transcribe with optional language specification
        transcribe_options = {}
        if language and language != 'auto':
            transcribe_options['language'] = language
        
        result = model.transcribe(
            audio_path,
            **transcribe_options,
            task='transcribe'  # Can also use 'translate' to translate to English
        )
        
        # Extract transcript text
        transcript_text = result.get('text', '').strip()
        detected_language = result.get('language', 'unknown')
        
        print(f"Transcription completed. Language: {detected_language}, Length: {len(transcript_text)} chars")
        
        return {
            'text': transcript_text,
            'language': detected_language,
            'status': 'success',
            'error': None
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"Transcription error: {error_msg}")
        return {
            'text': '',
            'language': '',
            'status': 'failed',
            'error': error_msg
        }

def transcribe_video(video_download):
    """
    Transcribe video using NCA Toolkit API (fast) or local Whisper (fallback)
    Also translates the transcript to Hindi automatically
    
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
    """
    # Try NCA Toolkit API first (much faster)
    if getattr(settings, 'NCA_API_ENABLED', False):
        nca_client = get_nca_client()
        if nca_client:
            try:
                print("Attempting transcription via NCA Toolkit API (fast)...")
                
                # Prefer video URL if available (no download needed)
                if video_download.video_url:
                    result = nca_client.transcribe_video(video_url=video_download.video_url)
                    if result['status'] == 'success':
                        # Translate to Hindi
                        transcript_text = result.get('text', '')
                        if transcript_text:
                            print(f"Translating transcript to Hindi...")
                            hindi_translation = translate_text(transcript_text, target='hi')
                            result['text_hindi'] = hindi_translation
                            print(f"NCA API transcription successful. Language: {result['language']}, Length: {len(transcript_text)} chars, Hindi: {len(hindi_translation)} chars")
                        return result
                    else:
                        print(f"NCA API transcription failed: {result.get('error')}. Falling back to local processing.")
                
                # Fallback: use local file if available
                if video_download.is_downloaded and video_download.local_file:
                    video_path = video_download.local_file.path
                    if os.path.exists(video_path):
                        result = nca_client.transcribe_video(video_file_path=video_path)
                        if result['status'] == 'success':
                            # Translate to Hindi
                            transcript_text = result.get('text', '')
                            if transcript_text:
                                print(f"Translating transcript to Hindi...")
                                hindi_translation = translate_text(transcript_text, target='hi')
                                result['text_hindi'] = hindi_translation
                                print(f"NCA API transcription successful. Language: {result['language']}, Length: {len(transcript_text)} chars, Hindi: {len(hindi_translation)} chars")
                            return result
                        else:
                            print(f"NCA API transcription failed: {result.get('error')}. Falling back to local processing.")
            except Exception as e:
                print(f"Error using NCA API: {e}. Falling back to local processing.")
    
    # Fallback to local Whisper transcription (slower but works offline)
    print("Using local Whisper transcription (slower)...")
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
        # Extract audio from video
        temp_audio_path = None
        try:
            audio_path = extract_audio_from_video(video_path)
            
            if not audio_path:
                return {
                    'text': '',
                    'language': '',
                    'status': 'failed',
                    'error': 'Failed to extract audio from video. Make sure ffmpeg is installed.'
                }
            
            temp_audio_path = audio_path
            
            # Transcribe audio
            print(f"Starting local Whisper transcription...")
            # Auto-detect language for Chinese/English videos
            transcript_result = transcribe_audio_local(
                audio_path,
                language=None,  # Auto-detect (will detect Chinese, English, etc.)
                model_size='base'  # Good balance of speed and accuracy
            )
            
            # Translate to Hindi if transcription was successful
            if transcript_result.get('status') == 'success' and transcript_result.get('text'):
                transcript_text = transcript_result.get('text', '')
                print(f"Translating transcript to Hindi...")
                hindi_translation = translate_text(transcript_text, target='hi')
                transcript_result['text_hindi'] = hindi_translation
                print(f"Translation complete. Original: {len(transcript_text)} chars, Hindi: {len(hindi_translation)} chars")
            
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
        return {
            'text': '',
            'language': '',
            'status': 'failed',
            'error': error_msg
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
        system_prompt = """You are an expert audio content creator. Your task is to create a detailed prompt for generating audio/voice-over from a video transcript.

The prompt should include:
1. Overall tone and mood (e.g., energetic, calm, informative)
2. Speaking style and pacing
3. Key emotions and emphasis points
4. Background music or sound effects suggestions
5. Target audience considerations

Be concise but comprehensive."""
        
        # Create user message
        user_message = f"""Video Title: {title}

Description: {description}

Transcript:
{transcript_text[:3000]}  

Please create a detailed audio generation prompt that will help create an engaging voice-over for this video content."""
        
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
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
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

