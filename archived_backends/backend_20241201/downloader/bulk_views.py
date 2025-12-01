from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import VideoDownload

@csrf_exempt
@require_http_methods(["POST"])
def bulk_delete_videos(request):
    """Delete multiple videos at once"""
    try:
        import json
        data = json.loads(request.body.decode('utf-8'))
        video_ids = data.get('video_ids', [])
        
        if not video_ids:
            return JsonResponse({"error": "No video IDs provided"}, status=400)
        
        # Delete videos
        deleted_count = VideoDownload.objects.filter(id__in=video_ids).delete()[0]
        
        return JsonResponse({
            "status": "success",
            "message": f"Deleted {deleted_count} video(s)",
            "deleted_count": deleted_count
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
