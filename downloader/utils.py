import re
import os
import json
import requests
import subprocess
from urllib.parse import urlparse
from django.core.files.base import ContentFile
from deep_translator import GoogleTranslator

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
