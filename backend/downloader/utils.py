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
        
        # Step 4.5: Translate summary to English if it's in another language
        # Detect if summary contains Chinese characters or other non-English content
        if any('\u4e00' <= char <= '\u9fff' for char in ai_summary):
            # Contains Chinese characters, translate to English
            print("Detected non-English content in summary. Translating to English...")
            try:
                ai_summary = translate_text(ai_summary, target='en')
                print(f"Summary translated to English: {ai_summary[:100]}...")
            except Exception as e:
                print(f"Translation failed: {e}. Using original summary.")
        
        # Step 5: Generate tags based on transcript and metadata
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

def transcribe_video(video_download):
    """
    Transcribe video using NCA Toolkit API.
    
    Args:
        video_download: VideoDownload model instance
        
    Returns:
        dict: {
            'text': str (full transcript),
            'language': str (detected language code),
            'status': 'success' or 'failed',
            'error': str (if failed)
        }
    """
    # Use NCA Toolkit API
    # We enforce this now as per user request, removing local fallback.
    
    if not getattr(settings, 'NCA_API_ENABLED', False):
        return {
            'text': '',
            'language': '',
            'status': 'failed',
            'error': 'NCA Toolkit API is disabled. Please enable it in settings to transcribe videos.'
        }

    nca_client = get_nca_client()
    if not nca_client:
        return {
            'text': '',
            'language': '',
            'status': 'failed',
            'error': 'Could not initialize NCA Toolkit client. Check your API configuration.'
        }

    try:
        print("Attempting transcription via NCA Toolkit API...")
        
        # Prefer uploading local file if available (more reliable than URL for Docker)
        if video_download.is_downloaded and video_download.local_file:
            video_path = video_download.local_file.path
            if os.path.exists(video_path):
                print(f"Uploading local file to NCA API: {video_path}")
                result = nca_client.transcribe_video(video_file_path=video_path)
                if result['status'] == 'success':
                    print(f"NCA API transcription successful. Language: {result['language']}, Length: {len(result['text'])} chars")
                    return result
                else:
                    print(f"Local file upload failed: {result.get('error')}. Falling back to video URL...")
                    # Don't return error yet, fall through to try video_url
        
        # Fallback: use video URL (might fail if blocked or not accessible from Docker)
        if video_download.video_url:
            print(f"Attempting transcription via URL: {video_download.video_url}")
            result = nca_client.transcribe_video(video_url=video_download.video_url)
            if result['status'] == 'success':
                print(f"NCA API transcription successful. Language: {result['language']}, Length: {len(result['text'])} chars")
                return result
            else:
                return {
                    'text': '',
                    'language': '',
                    'status': 'failed',
                    'error': f"NCA API transcription failed: {result.get('error')}"
                }
                
        return {
            'text': '',
            'language': '',
            'status': 'failed',
            'error': 'No local file or video URL available for transcription.'
        }

    except Exception as e:
        error_msg = str(e)
        print(f"Error using NCA API: {error_msg}")
        return {
            'text': '',
            'language': '',
            'status': 'failed',
            'error': f"NCA API Error: {error_msg}"
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
