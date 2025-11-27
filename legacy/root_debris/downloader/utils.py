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
        
        # Check if content is an M3U playlist (starts with #EXTM3U)
        if content.startswith(b'#EXTM3U') or content.startswith(b'#EXT-X-VERSION'):
            print(f"ERROR: Downloaded content is an M3U playlist, not a video file")
            print(f"Content preview: {content[:200]}")
            return None
        
        # Check minimum file size (very small files are likely errors)
        if len(content) < 10000:  # Less than 10KB is suspicious
            print(f"WARNING: Downloaded file is very small ({len(content)} bytes), might be an error page")
            # Check if it's HTML/error page
            if b'<html' in content.lower() or b'<!doctype' in content.lower():
                print(f"ERROR: Downloaded content appears to be HTML, not a video file")
                return None
        
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
                'summary': 'No content available for AI processing.',
                'tags': [],
                'transcript': '',
                'transcript_language': '',
                'status': 'failed',
                'error': 'No title, description, or transcript available'
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
                        print(f"NCA API transcription failed: {result.get('error')}. Falling back to local processing.")
                
                # Fallback: use local file if available
                if video_download.is_downloaded and video_download.local_file:
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
                    'error': error_msg
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
    Format the Hindi script with proper structure including title, voice prompt, and main content
    
    Args:
        raw_script: Raw script text from AI
        title: Video title
        
    Returns:
        str: Formatted script with sections
    """
    # Check if script already has the format
    if '**शीर्षक:**' in raw_script and '**आवाज़:**' in raw_script:
        # Ensure final CTA is present
        if 'आपकी मम्मी कसम सब्सक्राइब' not in raw_script:
            return raw_script + "\n\nआपकी मम्मी कसम सब्सक्राइब जरूर करे"
        return raw_script
    
    # Extract title for header - use a question format if it's a statement
    script_title = title if title else "वीडियो"
    # If title doesn't end with ?, make it a question format
    if script_title and not script_title.strip().endswith('?'):
        # Try to convert to question format, but keep original if it's already good
        pass
    
    # Default voice prompt
    voice_prompt = "माँ बाप की कसम, subscribe और like कर के जाओ अगर माँ बाप से प्यार करते हो तो! धन्यवाद!"
    
    # Format the script - CTA will be added later to ensure it's always at the end
    formatted = f"""**शीर्षक:** {script_title}

**आवाज़:** {voice_prompt}

{raw_script}"""
    
    return formatted.strip()


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

def get_clean_script_for_tts(formatted_script):
    """
    Extract clean script text for TTS (without formatting headers, timestamps, and questions)
    Only keeps main action/content description
    Removes introductory text and ensures CTA is at the end
    
    Args:
        formatted_script: Formatted script with headers
        
    Returns:
        str: Clean script text for TTS (only main content, no headers, timestamps, or questions) with CTA at end
    """
    if not formatted_script:
        return ""
    
    import re
    lines = formatted_script.split('\n')
    clean_lines = []
    skip_until_content = False
    skip_voice_prompt = False  # Track if we're in voice prompt section
    
    # Patterns to identify questions
    question_patterns = [
        r'क्या\s+',
        r'क्या\s+आप',
        r'क्या\s+ये',
        r'क्या\s+आपने',
        r'क्या\s+आपको',
        r'\?',  # Question mark
    ]
    
    # Patterns to identify introductory text to remove
    intro_patterns = [
        r'ठीक\s+है[,\s]*मैं\s+समझ\s+गया',
        r'यहाँ\s+स्क्रिप्ट\s+है',
        r'ठीक\s+है[,\s]*मैं\s+समझ\s+गया[।,]*\s*यहाँ\s+स्क्रिप्ट\s+है',
    ]
    
    # Patterns to identify voice prompt content
    voice_prompt_patterns = [
        r'माँ\s+बाप\s+की\s+कसम',
        r'subscribe\s+और\s+like',
        r'subscribe.*like',
        r'धन्यवाद',
        r'अगर\s+माँ\s+बाप\s+से\s+प्यार',
        r'कर\s+के\s+जाओ',
    ]
    
    for line in lines:
        original_line = line
        line = line.strip()
        
        # Skip header sections
        if line.startswith('**शीर्षक:**'):
            skip_until_content = True
            skip_voice_prompt = False
            continue
        elif line.startswith('**आवाज़:**'):
            skip_until_content = True
            skip_voice_prompt = True  # We're now in voice prompt section
            continue
        
        # Skip voice prompt content (lines after **आवाज़:** header)
        if skip_voice_prompt:
            # Check if this line contains voice prompt content
            is_voice_prompt = False
            for pattern in voice_prompt_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    is_voice_prompt = True
                    break
            
            # If it's voice prompt content or empty line, skip it
            if is_voice_prompt or not line:
                continue
            else:
                # If we hit content that's not voice prompt, we're past the voice prompt section
                skip_voice_prompt = False
        
        # Skip CTA line (we'll add it at the end)
        if 'आपकी मम्मी कसम' in line or 'सब्सक्राइब' in line:
            continue
        
        # Skip introductory text
        is_intro = False
        for pattern in intro_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                is_intro = True
                break
        
        if is_intro:
            continue
        
        # Skip empty lines after headers
        if skip_until_content and not line:
            continue
        
        # Start collecting content after headers (but not voice prompt)
        if skip_until_content and line and not skip_voice_prompt:
            skip_until_content = False
        
        # Add content lines (remove timestamps if present)
        if not skip_until_content and line:
            # Remove timestamp patterns like "00:00:00 " or "00:00:02 " at the start
            # Pattern matches: HH:MM:SS or MM:SS at the start of line
            line = re.sub(r'^\d{1,2}:\d{2}:\d{2}\s+', '', line)  # Remove HH:MM:SS
            line = re.sub(r'^\d{1,2}:\d{2}\s+', '', line)  # Remove MM:SS
            
            # Skip questions - check if line contains question patterns
            is_question = False
            for pattern in question_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    is_question = True
                    break
            
            # Only add non-empty lines that are not questions
            if line.strip() and not is_question:
                clean_lines.append(line.strip())
    
    # Join all clean lines
    clean_script = '\n'.join(clean_lines).strip()
    
    # ALWAYS add CTA at the end - append it properly formatted
    cta_text = "आपकी मम्मी कसम सब्सक्राइब जरूर करे"
    partial_cta = "आपकी मम्मी कसम सब्सक्राइब"
    
    if clean_script:
        # Check if CTA already exists at the end
        script_stripped = clean_script.strip()
        ends_with_full_cta = script_stripped.endswith(cta_text)
        ends_with_partial_cta = script_stripped.endswith(partial_cta) and not ends_with_full_cta
        
        # If CTA is already at the end, keep it as is
        if ends_with_full_cta:
            return clean_script
        
        # Remove CTA from anywhere in the script (to avoid duplicates)
        # Replace full CTA first
        if cta_text in clean_script:
            # Remove it but preserve the rest of the content
            clean_script = clean_script.replace(cta_text, "").strip()
        
        # Remove partial CTA if full CTA is not present
        if partial_cta in clean_script and cta_text not in clean_script:
            clean_script = clean_script.replace(partial_cta, "").strip()
        
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
    
    return clean_script


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
        system_prompt = """You are a content creator assistant. Generate engaging metadata for a Hindi video.
        
OUTPUT FORMAT (JSON only):
{
    "title": "Engaging Hindi title (50-60 characters, catchy and SEO-friendly)",
    "description": "Detailed Hindi description (2-3 paragraphs, 200-300 words, includes key points and call-to-action)",
    "tags": "tag1, tag2, tag3, tag4, tag5" (5-10 relevant tags in English, comma-separated)
}

REQUIREMENTS:
1. Title must be in HINDI (Devanagari script), engaging and click-worthy
2. Description must be in HINDI (Devanagari script), detailed and informative
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
        
        # Check if transcript has timestamps (format: 00:00:00 text)
        has_timestamps = bool(re.search(r'\d{1,2}:\d{2}:\d{2}\s+', transcript))
        
        # If transcript has timestamps, use it directly and convert to Hindi if needed
        if transcript and has_timestamps:
            # Parse transcript with timestamps
            lines = transcript.split('\n')
            timestamped_lines = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Extract timestamp and text
                timestamp_match = re.match(r'^(\d{1,2}:\d{2}:\d{2})\s+(.+)$', line)
                if timestamp_match:
                    timestamp = timestamp_match.group(1)
                    text = timestamp_match.group(2)
                    
                    # Check if text is already in Hindi (contains Devanagari characters)
                    has_devanagari = bool(re.search(r'[\u0900-\u097F]', text))
                    
                    if has_devanagari:
                        # Already in Hindi, use as-is
                        timestamped_lines.append(f"{timestamp} {text}")
                    else:
                        # Translate to Hindi
                        hindi_text = translate_text(text, target='hi')
                        timestamped_lines.append(f"{timestamp} {hindi_text}")
                else:
                    # Line without timestamp, check if it's Hindi
                    has_devanagari = bool(re.search(r'[\u0900-\u097F]', line))
                    if has_devanagari:
                        timestamped_lines.append(line)
                    else:
                        # Translate to Hindi
                        hindi_text = translate_text(line, target='hi')
                        timestamped_lines.append(hindi_text)
            
            # Format the script with title, voice prompt, and timestamped content
            script_parts = []
            
            # Add title section
            script_parts.append(f"**शीर्षक:** {title}")
            
            # Add voice prompt section
            script_parts.append(f"**आवाज़:** माँ बाप की कसम, subscribe और like कर के जाओ अगर माँ बाप से प्यार करते हो तो! धन्यवाद!")
            
            # Add timestamped content
            script_parts.append("\n".join(timestamped_lines))
            
            # Add CTA at the end
            cta_text = "आपकी मम्मी कसम सब्सक्राइब जरूर करे"
            script_parts.append(cta_text)
            
            formatted_script = "\n\n".join(script_parts)
            
            return {
                'script': formatted_script,
                'status': 'success',
                'error': None
            }
        
        # If no timestamped transcript, fall back to AI generation
        # Prefer Hindi transcript if available, otherwise use original transcript
        content_for_script = transcript_hindi if transcript_hindi else transcript
        
        # If no transcript available, use title and description
        if not content_for_script:
            content_for_script = f"{title}. {description}"
        
        # Create system prompt for Hindi script generation
        system_prompt = """आप एक विशेषज्ञ स्क्रिप्ट राइटर हैं जो वीडियो कंटेंट के लिए हिंदी में प्राकृतिक और आकर्षक स्क्रिप्ट बनाते हैं।

आपका कार्य:
1. वीडियो की सामग्री को समझकर एक प्राकृतिक हिंदी स्क्रिप्ट बनाएं
2. स्क्रिप्ट को वीडियो की अवधि के अनुसार समायोजित करें
3. स्क्रिप्ट को बोलने योग्य, प्राकृतिक और आकर्षक बनाएं
4. स्क्रिप्ट को निम्नलिखित फॉर्मेट में बनाएं:

**शीर्षक:** [वीडियो का शीर्षक या एक आकर्षक हेडलाइन]

**आवाज़:** [एक आकर्षक वॉयस प्रॉम्प्ट जैसे "माँ बाप की कसम, subscribe और like कर के जाओ अगर माँ बाप से प्यार करते हो तो! धन्यवाद!"]

[मुख्य स्क्रिप्ट सामग्री - वीडियो की सामग्री के आधार पर]

[अंत में CTA: "आपकी मम्मी कसम सब्सक्राइब जरूर करे"]

महत्वपूर्ण निर्देश:
- स्क्रिप्ट पूरी तरह से हिंदी (देवनागरी) में होनी चाहिए
- **रोजमर्रा की बोलचाल की हिंदी इस्तेमाल करें - formal या शुद्ध हिंदी नहीं**
- स्क्रिप्ट प्राकृतिक और बोलने योग्य होनी चाहिए
- वीडियो की अवधि को ध्यान में रखते हुए स्क्रिप्ट की लंबाई निर्धारित करें
- **सीधे बिंदु पर आएं - कोई ग्रीटिंग, नमस्कार, या परिचयात्मक वाक्य नहीं**
- **धन्यवाद या समापन वाक्य नहीं - सीधे कंटेंट का वर्णन शुरू करें**
- **स्क्रिप्ट सीधे वीडियो में हो रही एक्शन/घटना का वर्णन करे - सवाल बिल्कुल नहीं**
- **कोई भी सवाल नहीं - सिर्फ वर्णन और एक्शन**
- **पहली लाइन सीधे एक्शन से शुरू होनी चाहिए, सवाल नहीं**
- **सिर्फ मुख्य कंटेंट - वीडियो में क्या हो रहा है उसका वर्णन, बाकी सब हटाएं**
- उदाहरण (सही): "00:00:00 देखो इस लड़की ने अपनी सोई हुई दोस्तों के" - सीधे एक्शन
- उदाहरण (गलत): "00:00:00 क्या आपने कभी इतनी छोटी बंदूक देखी है?" - सवाल नहीं
- उदाहरण (गलत): "क्या आपको भी ये पसंद आई?" - सवाल नहीं
- **शीर्षक:** और **आवाज़:** सेक्शन जरूर शामिल करें
- अंत में "आपकी मम्मी कसम सब्सक्राइब जरूर करे" जरूर जोड़ें
- **बिल्कुल बचें:** "क्या आपने...", "क्या आपको...", "क्या ये...", "नमस्कार दोस्तों", "दिल थाम के बैठिए", "आज हम देखेंगे", "चलिए शुरू करते हैं" जैसे वाक्यों से
- **सिर्फ मुख्य कंटेंट - वीडियो में जो हो रहा है उसका सीधा वर्णन, कोई सवाल नहीं, कोई अतिरिक्त बात नहीं**"""
        
        # Create user message with video details
        duration_text = f"{int(duration)} सेकंड" if duration > 0 else "अज्ञात अवधि"
        
        user_message = f"""वीडियो शीर्षक: {title}
विवरण: {description}
अवधि: {duration_text}

**मूल ट्रांसक्रिप्ट (Original Transcript):**
{content_for_script[:4000]}

**महत्वपूर्ण निर्देश:**
1. **मूल ट्रांसक्रिप्ट का उपयोग करें - नई सामग्री न बनाएं**
2. **अगर ट्रांसक्रिप्ट में टाइमस्टैम्प हैं (जैसे 00:00:00), तो उन्हें बनाए रखें**
3. **अगर ट्रांसक्रिप्ट हिंदी में नहीं है, तो हिंदी में अनुवाद करें लेकिन टाइमस्टैम्प बनाए रखें**
4. **अगर ट्रांसक्रिप्ट में टाइमस्टैम्प नहीं हैं, तो वीडियो की अवधि के अनुसार समय-आधारित सेगमेंट में विभाजित करें**
5. **सीधे बिंदु पर आएं - कोई ग्रीटिंग या परिचय नहीं**
6. **स्क्रिप्ट सीधे वीडियो में हो रही एक्शन/घटना का वर्णन करे - मूल ट्रांसक्रिप्ट के आधार पर**
7. **रोजमर्रा की बोलचाल की हिंदी इस्तेमाल करें**

**उदाहरण (मूल ट्रांसक्रिप्ट के आधार पर):**
अगर मूल ट्रांसक्रिप्ट है:
00:00:00 देखो घर पर मम्मी ना होने के कारण इस
00:00:01 बच्चे ने घर पर अंडे से खेलना शुरू कर दिया

तो आउटपुट होना चाहिए (टाइमस्टैम्प बनाए रखें):
00:00:00 देखो घर पर मम्मी ना होने के कारण इस
00:00:01 बच्चे ने घर पर अंडे से खेलना शुरू कर दिया

**गलत (इससे बिल्कुल बचें):**
- नई सामग्री बनाना (जो मूल ट्रांसक्रिप्ट में नहीं है)
- टाइमस्टैम्प हटाना
- सवाल जोड़ना (जैसे "क्या आपने...")
- ग्रीटिंग जोड़ना (जैसे "नमस्कार दोस्तों")

**याद रखें: मूल ट्रांसक्रिप्ट का उपयोग करें, टाइमस्टैम्प बनाए रखें, सिर्फ हिंदी में कन्वर्ट करें**"""
        
        # Call AI API
        provider = settings_obj.provider
        api_key = settings_obj.api_key
        
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
            script = result['prompt'].strip()
            
            # Remove questions from the script before formatting
            script = remove_questions_from_script(script)
            
            # Format the script with proper structure
            formatted_script = format_hindi_script(script, title)
            
            # ALWAYS ensure CTA "आपकी मम्मी कसम सब्सक्राइब जरूर करे" is present at the end
            # Remove any existing CTA at the end first, then add it
            cta_text = "आपकी मम्मी कसम सब्सक्राइब जरूर करे"
            cta_text_old = "आपकी मम्मी कसम सब्सक्राइब"  # Old version without जरूर करे
            
            # Remove trailing CTA if it exists (to avoid duplicates)
            formatted_script = formatted_script.rstrip()
            
            # Check for new CTA format
            if formatted_script.endswith(cta_text):
                formatted_script = formatted_script[:-len(cta_text)].rstrip()
            elif formatted_script.endswith(cta_text + "\n"):
                formatted_script = formatted_script[:-len(cta_text + "\n")].rstrip()
            elif formatted_script.endswith("\n\n" + cta_text):
                formatted_script = formatted_script[:-len("\n\n" + cta_text)].rstrip()
            # Check for old CTA format (without जरूर करे)
            elif formatted_script.endswith(cta_text_old):
                formatted_script = formatted_script[:-len(cta_text_old)].rstrip()
            elif formatted_script.endswith(cta_text_old + "\n"):
                formatted_script = formatted_script[:-len(cta_text_old + "\n")].rstrip()
            elif formatted_script.endswith("\n\n" + cta_text_old):
                formatted_script = formatted_script[:-len("\n\n" + cta_text_old)].rstrip()
            
            # Always add CTA at the end
            formatted_script += f"\n\n{cta_text}"
            
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

