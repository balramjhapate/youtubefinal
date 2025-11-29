"""
Utility functions adapted from Django utils.py
Framework-agnostic business logic
"""
import re
import os
import json
import requests
import subprocess
import tempfile
from urllib.parse import urlparse
from pathlib import Path
from io import BytesIO
from deep_translator import GoogleTranslator
from app.config import settings
from app.services.nca_toolkit_client import get_nca_client


def extract_video_id(url):
    """Extract unique video ID from URL (supports multiple platforms)"""
    source = detect_video_source(url)
    
    if source == 'youtube':
        # YouTube: extract from watch?v=, youtu.be/, or /shorts/
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',  # watch?v= or youtu.be/
            r'shorts\/([0-9A-Za-z_-]{11})',     # /shorts/VIDEO_ID
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    elif source == 'xiaohongshu':
        # Xiaohongshu: extract from /item/ID
        path = urlparse(url).path
        match = re.search(r'/item/([a-zA-Z0-9]+)', path)
        if match:
            return match.group(1)
        return None
    else:
        # For other platforms, try to extract any ID-like pattern
        # This is a fallback
        path = urlparse(url).path
        match = re.search(r'/([a-zA-Z0-9_-]{8,})', path)
        if match:
            return match.group(1)
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


def detect_video_source(url):
    """Detect the video source from URL"""
    url_lower = url.lower()
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif 'xiaohongshu.com' in url_lower or 'xhslink.com' in url_lower or 'xhs.cn' in url_lower:
        return 'xiaohongshu'
    elif 'facebook.com' in url_lower or 'fb.com' in url_lower:
        return 'facebook'
    elif 'instagram.com' in url_lower or 'instagr.am' in url_lower:
        return 'instagram'
    elif 'vimeo.com' in url_lower:
        return 'vimeo'
    else:
        return 'unknown'


def perform_extraction(url):
    """Perform video extraction using multiple methods"""
    source = detect_video_source(url)
    print(f"Detected video source: {source} for URL: {url}")
    
    # For YouTube, use yt-dlp directly (best support)
    if source == 'youtube':
        print(f"Extracting YouTube video via yt-dlp: {url}")
        video_data = extract_video_ytdlp(url)
        if video_data:
            video_data['method'] = 'yt-dlp'
            return video_data
        print(f"yt-dlp failed for YouTube URL")
        return None
    
    # For Xiaohongshu/RedNote, try Seekin API first, then yt-dlp
    if source == 'xiaohongshu':
        # Priority 1: Try Seekin.ai API
        print(f"Attempting extraction via Seekin.ai API: {url}")
        video_data = extract_video_seekin(url)
        if video_data:
            video_data['method'] = 'seekin'
            return video_data

        # Priority 2: yt-dlp
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
    else:
        # For other sources (Facebook, Instagram, Vimeo, etc.), use yt-dlp
        print(f"Extracting {source} video via yt-dlp: {url}")
        video_data = extract_video_ytdlp(url)
        if video_data:
            video_data['method'] = 'yt-dlp'
            return video_data
    
    return None


def extract_video_seekin(url):
    """Extract video using Seekin.ai API"""
    try:
        api_url = "https://api.seekin.ai/ikool/media/download"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        payload = {"url": url}
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") == "0000" and data.get("data"):
            video_data = data["data"]
            medias = video_data.get("medias", [])
            video_url = None
            
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
                    "original_description": title,
                    "duration": video_data.get("duration", 0)
                }
        
        return None
    except Exception as e:
        print(f"Seekin API error: {e}")
        return None


def extract_video_ytdlp(url):
    """Extract video using yt-dlp"""
    try:
        import sys
        python_exe = sys.executable
        
        # Always use pip-installed yt-dlp (python -m yt_dlp) - most reliable
        # The binary file in backend/ requires Python 3.10+ and may not work
        # Check if yt-dlp is installed as a Python package
        test_result = subprocess.run(
            [python_exe, '-m', 'yt_dlp', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if test_result.returncode != 0:
            print("Error: yt-dlp not installed. Please install: pip install yt-dlp")
            return None
        
        print(f"Using pip-installed yt-dlp (version: {test_result.stdout.strip()})")

        # Build command - always use python -m yt_dlp (pip installed)
        cmd = [python_exe, '-m', 'yt_dlp', '--dump-json', '--no-warnings']
        
        # Add format selection for better quality
        source = detect_video_source(url)
        if source == 'youtube':
            # For YouTube, prefer best quality but allow fallback
            # Try: best video+audio, then best mp4, then best overall
            cmd.extend(['-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'])
        else:
            # For other platforms, use best available
            cmd.extend(['-f', 'best'])
        
        cmd.append(url)
        
        print(f"Running yt-dlp: {' '.join(cmd[:3])}... [format] [URL]")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60  # Increased timeout for YouTube
        )

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout
            print(f"yt-dlp error (exit code {result.returncode}):")
            # Log more details for debugging
            if result.stderr:
                stderr_text = result.stderr[:1000] if len(result.stderr) > 1000 else result.stderr
                print(f"yt-dlp stderr: {stderr_text}")
            if result.stdout:
                stdout_text = result.stdout[:1000] if len(result.stdout) > 1000 else result.stdout
                print(f"yt-dlp stdout: {stdout_text}")
            
            # Extract meaningful error message
            error_lines = (result.stderr or result.stdout or "").split('\n')
            meaningful_error = None
            for line in error_lines:
                if any(keyword in line.lower() for keyword in ['error', 'unable', 'failed', 'not found', 'private', 'unavailable']):
                    meaningful_error = line.strip()
                    break
            
            if meaningful_error:
                print(f"Meaningful error: {meaningful_error}")
            
            return None

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            print(f"Failed to parse yt-dlp JSON output: {e}")
            print(f"yt-dlp stdout: {result.stdout[:1000]}")
            return None
        
        # For YouTube DASH videos, URL is in requested_formats, not top-level 'url'
        video_url = data.get('url')
        
        # Try requested_formats first (for DASH videos)
        if not video_url:
            requested_formats = data.get('requested_formats', [])
            if requested_formats:
                # Find the video format (not audio-only)
                for fmt in requested_formats:
                    if fmt.get('vcodec') != 'none' and fmt.get('url'):
                        video_url = fmt.get('url')
                        print(f"Found video URL in requested_formats: {video_url[:100]}...")
                        break
        
        # Fallback to formats if still no URL
        if not video_url:
            formats = data.get('formats', [])
            if formats:
                # Filter for video formats (not audio-only)
                video_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('url')]
                if video_formats:
                    # Sort by quality and get best - handle None values properly
                    def get_quality_score(fmt):
                        height = fmt.get('height')
                        quality = fmt.get('quality', 0)
                        # Convert quality string to number if needed
                        if isinstance(quality, str):
                            try:
                                quality = int(quality.replace('p', ''))
                            except:
                                quality = 0
                        # Return height if available, otherwise quality, otherwise 0
                        return (height if height is not None else 0) or (quality if quality is not None else 0) or 0
                    
                    best_video = sorted(video_formats, key=get_quality_score, reverse=True)[0]
                    video_url = best_video.get('url')
                    print(f"Found video URL in formats: {video_url[:100]}...")

        if video_url:
            title = data.get('title', 'Video')
            description = data.get('description', '')
            duration = int(data.get('duration', 0)) if data.get('duration') else 0
            
            # Get thumbnail - try multiple fields
            thumbnail = data.get('thumbnail') or data.get('thumbnails', [{}])[0].get('url') if data.get('thumbnails') else None
            
            return {
                "video_url": video_url,
                "title": title,
                "cover_url": thumbnail,
                "original_title": title,
                "original_description": description,
                "duration": duration
            }
        
        return None
    except json.JSONDecodeError as e:
        print(f"yt-dlp JSON decode error: {e}")
        print(f"yt-dlp output: {result.stdout[:500] if 'result' in locals() else 'N/A'}")
        return None
    except Exception as e:
        print(f"yt-dlp extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def extract_video_requests(url):
    """Extract video using direct HTTP requests"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.xiaohongshu.com/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
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
                duration = video_info.get('duration', 0)
                
                return {
                    "video_url": video_url,
                    "title": title,
                    "cover_url": cover_url,
                    "original_title": title,
                    "original_description": desc,
                    "duration": duration
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
        return BytesIO(response.content)
    except Exception as e:
        print(f"Download error: {e}")
        return None


def process_video_with_ai(video_download):
    """
    Process video with AI to generate summary and tags
    """
    try:
        transcript_text = ''
        transcript_language = ''
        
        # Use existing transcript if available
        if hasattr(video_download, 'transcript') and video_download.transcript and \
           hasattr(video_download, 'transcription_status') and video_download.transcription_status == 'transcribed':
            transcript_text = video_download.transcript
            transcript_language = getattr(video_download, 'transcript_language', '') or ''
            print(f"Using existing transcript. Language: {transcript_language}, Length: {len(transcript_text)} chars")
        else:
            print("No existing transcript found. AI processing will use metadata only.")
        
        # Extract available information
        title = getattr(video_download, 'title', '') or getattr(video_download, 'original_title', '') or ""
        description = getattr(video_download, 'description', '') or getattr(video_download, 'original_description', '') or ""
        
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
                'status': 'failed',
                'error': 'No title, description, or transcript available'
            }
        
        # Generate summary
        summary_parts = []
        
        if transcript_text:
            if len(transcript_text) > 300:
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
            if title:
                summary_parts.append(f"This video is about: {title}")
            if description:
                desc_summary = description.split('.')[0] if '.' in description else description[:200]
                summary_parts.append(f"Description: {desc_summary}")
        
        ai_summary = " | ".join(summary_parts) if summary_parts else "AI analysis completed."
        
        # Translate summary to English if needed
        if any('\u4e00' <= char <= '\u9fff' for char in ai_summary):
            print("Detected non-English content in summary. Translating to English...")
            try:
                ai_summary = translate_text(ai_summary, target='en')
                print(f"Summary translated to English: {ai_summary[:100]}...")
            except Exception as e:
                print(f"Translation failed: {e}. Using original summary.")
        
        # Generate tags
        tags = []
        text_for_tags = transcript_text if transcript_text else f"{title} {description}"
        
        if text_for_tags:
            words = re.findall(r'\b\w{4,}\b', text_for_tags.lower())
            stop_words = {
                'the', 'this', 'that', 'with', 'from', 'have', 'been', 'they', 'what',
                'your', 'some', 'will', 'very', 'just', 'like', 'them', 'then', 'than',
                'and', 'are', 'but', 'not', 'you', 'all', 'can', 'her', 'was', 'one',
                'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new',
                'now', 'old', 'see', 'two', 'way', 'who', 'its'
            }
            
            word_count = {}
            for word in words:
                if word not in stop_words and len(word) > 3:
                    word_count[word] = word_count.get(word, 0) + 1
            
            sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
            tags.extend([word for word, count in sorted_words[:8]])
        
        if transcript_language:
            if transcript_language.startswith('zh'):
                tags.append('chinese-content')
            elif transcript_language.startswith('en'):
                tags.append('english-content')
        
        if len(transcript_text) > 500:
            tags.append('long-form')
        
        if not tags:
            tags = ['content', 'social-media', 'video']
        
        return {
            'summary': ai_summary,
            'tags': tags[:10],
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
    Transcribe video using NCA Toolkit API
    """
    if not settings.NCA_API_ENABLED:
        return {
            'text': '',
            'language': '',
            'status': 'failed',
            'error': 'NCA Toolkit API is disabled. Please enable it in settings.'
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
        
        # Prefer local file if available
        if hasattr(video_download, 'is_downloaded') and video_download.is_downloaded and \
           hasattr(video_download, 'local_file') and video_download.local_file:
            video_path = video_download.local_file
            if os.path.exists(video_path):
                print(f"Uploading local file to NCA API: {video_path}")
                result = nca_client.transcribe_video(video_file_path=video_path)
                if result['status'] == 'success':
                    print(f"NCA API transcription successful. Language: {result['language']}, Length: {len(result['text'])} chars")
                    return result
                else:
                    print(f"Local file upload failed: {result.get('error')}. Falling back to video URL...")
        
        # Fallback: use video URL
        if hasattr(video_download, 'video_url') and video_download.video_url:
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

