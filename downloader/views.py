import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import VideoDownload
from .utils import perform_extraction, extract_video_id, translate_text

def index(request):
    """Redirect homepage to admin login"""
    return redirect('/admin/')

@csrf_exempt
@require_http_methods(["POST"])
def extract_video(request):
    """API endpoint to extract video from Xiaohongshu URL"""
    try:
        data = json.loads(request.body.decode('utf-8'))
        url = data.get('url')
        
        if not url:
            return JsonResponse({"error": "URL is required"}, status=400)
        
        # Check for existing video by ID first
        video_id = extract_video_id(url)
        if video_id:
            existing = VideoDownload.objects.filter(video_id=video_id).first()
            if existing and existing.status == 'success':
                return JsonResponse({
                    "video_url": existing.video_url,
                    "title": existing.title,
                    "cover_url": existing.cover_url,
                    "method": existing.extraction_method,
                    "cached": True
                })
        
        # Create a pending download record
        download = VideoDownload.objects.create(
            url=url,
            video_id=video_id,
            status='pending'
        )
        
        # Try extraction
        video_data = perform_extraction(url)
        
        if video_data:
            # Update the download record with success
            download.status = 'success'
            download.extraction_method = video_data.get('method', '')
            download.video_url = video_data.get('video_url', '')
            download.cover_url = video_data.get('cover_url', '')
            
            # Translate Content
            original_title = video_data.get('original_title', '')
            original_desc = video_data.get('original_description', '')
            
            download.original_title = original_title
            download.original_description = original_desc
            
            download.title = translate_text(original_title, target='en')
            download.description = translate_text(original_desc, target='en')
            
            download.save()
            
            return JsonResponse({
                "video_url": download.video_url,
                "title": download.title,
                "cover_url": download.cover_url,
                "method": download.extraction_method
            })
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
