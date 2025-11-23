import json
import re
import subprocess
import os
import requests
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import VideoDownload


def index(request):
    """Homepage view"""
    return render(request, 'downloader/index.html')


@csrf_exempt
@require_http_methods(["POST"])
def extract_video(request):
    """API endpoint to extract video from Xiaohongshu URL"""
    try:
        data = json.loads(request.body.decode('utf-8'))
        url = data.get('url')
        
        if not url:
            return JsonResponse({"error": "URL is required"}, status=400)
        
        # Create a pending download record
        download = VideoDownload.objects.create(
            url=url,
            status='pending'
        )
        
        # Try extraction
        video_data = perform_extraction(url)
        
        if video_data:
            # Update the download record with success
            download.title = video_data.get('title', 'Xiaohongshu Video')
            download.video_url = video_data.get('video_url', '')
            download.cover_url = video_data.get('cover_url', '')
            download.extraction_method = video_data.get('method', '')
            download.status = 'success'
            download.save()
            
            return JsonResponse(video_data)
        else:
            # Update the download record with failure
            download.status = 'failed'
            download.error_message = "Could not extract video. The link might be invalid or protected."
            download.save()
            
            return JsonResponse({
                "error": "Could not extract video. The link might be invalid or protected."
            }, status=400)
            
    except Exception as e:
        # Update the download record with error
        if 'download' in locals():
            download.status = 'failed'
            download.error_message = str(e)
            download.save()
        
        return JsonResponse({"error": str(e)}, status=400)


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
                return {
                    "video_url": video_url,
                    "title": video_data.get("title", "Xiaohongshu Video"),
                    "cover_url": video_data.get("imageUrl")
                }
        
        print(f"Seekin API returned invalid data: {data}")
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
            # Fallback to global command if local binary not found
            yt_dlp_path = 'yt-dlp'

        result = subprocess.run(
            [yt_dlp_path, '--dump-json', url],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            print(f"yt-dlp error: {result.stderr}")
            return None

        data = json.loads(result.stdout)
        
        # yt-dlp returns the direct video url in 'url' or 'requested_downloads'
        video_url = data.get('url')
        if not video_url:
            # Check formats
            formats = data.get('formats', [])
            if formats:
                # Get best video
                best_video = sorted(formats, key=lambda x: x.get('height', 0), reverse=True)[0]
                video_url = best_video.get('url')

        if video_url:
            return {
                "video_url": video_url,
                "title": data.get('title', 'Xiaohongshu Video'),
                "cover_url": data.get('thumbnail')
            }
        
        return None

    except Exception as e:
        print(f"yt-dlp extraction failed: {e}")
        return None


def extract_video_requests(url):
    """Extract video using direct HTTP requests"""
    print("Fallback to requests extraction...")
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
                cover_url = note_data.get('imageList', [{}])[0].get('url') if note_data.get('imageList') else None
                
                return {
                    "video_url": video_url,
                    "title": title,
                    "cover_url": cover_url
                }
        
        return None

    except Exception as e:
        print(f"Requests extraction error: {e}")
        return None
