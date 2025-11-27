import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
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
            if existing:
                if existing.status == 'success':
                    return JsonResponse({
                        "video_url": existing.video_url,
                        "title": existing.title,
                        "cover_url": existing.cover_url,
                        "method": existing.extraction_method,
                        "cached": True
                    })
                else:
                    # Video exists but extraction failed, return error
                    return JsonResponse({
                        "error": f"Video with ID '{video_id}' already exists but extraction failed."
                    }, status=400)
        
        # Check if video_id already exists before creating (race condition protection)
        if video_id and VideoDownload.objects.filter(video_id=video_id).exists():
            return JsonResponse({
                "error": f"Video with ID '{video_id}' already exists."
            }, status=400)
        
        # Create a pending download record
        try:
            download = VideoDownload.objects.create(
                url=url,
                video_id=video_id,  # Can be None now
                status='pending'
            )
        except Exception as e:
            if 'video_id' in str(e) or 'UNIQUE constraint' in str(e):
                # Duplicate detected (race condition)
                if video_id:
                    existing = VideoDownload.objects.filter(video_id=video_id).first()
                    if existing:
                        return JsonResponse({
                            "error": f"Video with ID '{video_id}' already exists."
                        }, status=400)
            raise
        
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

from .models import AIProviderSettings

@csrf_exempt
@require_http_methods(["GET", "POST"])
def ai_settings(request):
    """GET returns current AI provider settings, POST updates them."""
    if request.method == "GET":
        try:
            settings = AIProviderSettings.objects.first()
            if not settings:
                return JsonResponse({"provider": "gemini", "api_key": ""})
            return JsonResponse({"provider": settings.provider, "api_key": settings.api_key})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:  # POST
        try:
            data = json.loads(request.body.decode('utf-8'))
            provider = data.get('provider', 'gemini')
            api_key = data.get('api_key', '')
            settings, created = AIProviderSettings.objects.get_or_create(id=1, defaults={"provider": provider, "api_key": api_key})
            if not created:
                settings.provider = provider
                settings.api_key = api_key
                settings.save()
            return JsonResponse({"status": "saved"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)




@csrf_exempt
@require_http_methods(["GET"])
def list_videos(request):
    """API endpoint to list videos with optional filtering"""
    try:
        # Get query parameters
        status = request.GET.get('status')
        transcription_status = request.GET.get('transcription_status')
        search = request.GET.get('search')
        
        # Base query
        queryset = VideoDownload.objects.all()
        
        # Apply filters
        if status:
            queryset = queryset.filter(status=status)
        
        if transcription_status:
            queryset = queryset.filter(transcription_status=transcription_status)
            
        if search:
            queryset = queryset.filter(title__icontains=search)
            
        # Serialize data
        videos = []
        for video in queryset:
            videos.append({
                "id": video.id,
                "url": video.url,
                "title": video.title,
                "original_title": video.original_title,
                "description": video.description,
                "cover_url": video.cover_url,
                "video_url": video.video_url,
                "status": video.status,
                "transcription_status": video.transcription_status,
                "ai_processing_status": video.ai_processing_status,
                "audio_prompt_status": video.audio_prompt_status,
                "transcript_hindi": video.transcript_hindi,
                "is_downloaded": video.is_downloaded,
                "extraction_method": video.extraction_method,
                "created_at": video.created_at.isoformat(),
            })
            
        return JsonResponse(videos, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@csrf_exempt
@require_http_methods(["POST"])
def download_video(request, video_id):
    """Download video locally"""
    try:
        from .utils import download_file
        
        video = VideoDownload.objects.get(id=video_id)
        if not video.video_url:
            return JsonResponse({"error": "No video URL found"}, status=400)
            
        # Download the file
        file_content = download_file(video.video_url)
        if file_content:
            # Save to local_file field
            filename = f"{video.video_id or 'video'}_{video.pk}.mp4"
            video.local_file.save(filename, file_content, save=True)
            
            # Update status
            video.is_downloaded = True
            video.save()
            
            return JsonResponse({"status": "success", "message": "Video downloaded successfully"})
        else:
            return JsonResponse({"error": "Failed to download video file"}, status=500)
            
    except VideoDownload.DoesNotExist:
        return JsonResponse({"error": "Video not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def transcribe_video_view(request, video_id):
    """Start transcription with Hindi translation"""
    try:
        from .utils import transcribe_video, translate_text
        
        video = VideoDownload.objects.get(id=video_id)
        
        # Update status to transcribing
        video.transcription_status = 'transcribing'
        video.transcript_started_at = timezone.now()
        video.save()
        
        # Perform transcription
        result = transcribe_video(video)
        
        if result['status'] == 'success':
            video.transcript = result['text']
            video.transcript_language = result['language']
            video.transcription_status = 'transcribed'
            video.transcript_processed_at = timezone.now()
            
            # Translate to Hindi using Gemini AI
            if video.transcript:
                try:
                    video.transcript_hindi = translate_text(video.transcript, target='hi')
                except Exception as e:
                    print(f"Hindi translation failed: {e}")
                    video.transcript_hindi = ""
            
            video.save()
            return JsonResponse({
                "status": "success",
                "message": "Transcription completed",
                "transcript": video.transcript,
                "transcript_hindi": video.transcript_hindi,
                "language": video.transcript_language
            })
        else:
            video.transcription_status = 'failed'
            video.transcript_error_message = result.get('error', 'Unknown error')
            video.save()
            return JsonResponse({"error": result.get('error', 'Transcription failed')}, status=500)
            
    except VideoDownload.DoesNotExist:
        return JsonResponse({"error": "Video not found"}, status=404)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in transcribe_video_view: {str(e)}")
        print(f"Traceback: {error_trace}")
        
        if 'video' in locals():
            video.transcription_status = 'failed'
            video.transcript_error_message = str(e)
            video.save()
        
        # Return a more user-friendly error message
        error_message = str(e)
        if 'NCA_API' in error_message or 'NCA' in error_message:
            error_message = f"Transcription service error: {error_message}"
        return JsonResponse({"error": error_message}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_transcription_status(request, video_id):
    """Get transcription status"""
    try:
        video = VideoDownload.objects.get(id=video_id)
        return JsonResponse({
            "status": video.transcription_status,
            "transcript": video.transcript,
            "language": video.transcript_language
        })
    except VideoDownload.DoesNotExist:
        return JsonResponse({"error": "Video not found"}, status=404)

@csrf_exempt
@require_http_methods(["POST"])
def process_ai_view(request, video_id):
    """Start AI processing to generate summary and tags"""
    try:
        from .utils import process_video_with_ai
        
        video = VideoDownload.objects.get(id=video_id)
        
        # Update status to processing
        video.ai_processing_status = 'processing'
        video.save()
        
        # Perform AI processing
        result = process_video_with_ai(video)
        
        if result['status'] == 'success':
            video.ai_summary = result['summary']
            video.ai_tags = ','.join(result['tags'])
            video.ai_processing_status = 'processed'
            video.ai_processed_at = timezone.now()
            video.save()
            
            return JsonResponse({
                "status": "success",
                "message": "AI processing completed",
                "summary": video.ai_summary,
                "tags": video.ai_tags
            })
        else:
            video.ai_processing_status = 'failed'
            video.ai_error_message = result.get('error', 'Unknown error')
            video.save()
            return JsonResponse({"error": result.get('error', 'AI processing failed')}, status=500)
            
    except VideoDownload.DoesNotExist:
        return JsonResponse({"error": "Video not found"}, status=404)
    except Exception as e:
        if 'video' in locals():
            video.ai_processing_status = 'failed'
            video.ai_error_message = str(e)
            video.save()
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def generate_audio_prompt_view(request, video_id):
    """Generate audio prompt"""
    try:
        video = VideoDownload.objects.get(id=video_id)
        video.audio_prompt_status = 'generating'
        video.save()
        return JsonResponse({"status": "success", "message": "Audio prompt generation started"})
    except VideoDownload.DoesNotExist:
        return JsonResponse({"error": "Video not found"}, status=404)

@csrf_exempt
@require_http_methods(["POST"])
def synthesize_audio_view(request, video_id):
    """Synthesize audio"""
    try:
        video = VideoDownload.objects.get(id=video_id)
        return JsonResponse({"status": "success", "message": "Audio synthesis started"})
    except VideoDownload.DoesNotExist:
        return JsonResponse({"error": "Video not found"}, status=404)

@csrf_exempt
@require_http_methods(["PATCH"])
def update_voice_profile_view(request, video_id):
    """Update voice profile"""
    try:
        video = VideoDownload.objects.get(id=video_id)
        return JsonResponse({"status": "success", "message": "Voice profile updated"})
    except VideoDownload.DoesNotExist:
        return JsonResponse({"error": "Video not found"}, status=404)

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_video(request, video_id):
    """Delete video"""
    try:
        video = VideoDownload.objects.get(id=video_id)
        video.delete()
        return JsonResponse({"status": "success", "message": "Video deleted"})
    except VideoDownload.DoesNotExist:
        return JsonResponse({"error": "Video not found"}, status=404)

@csrf_exempt
@require_http_methods(["GET"])
def get_video(request, video_id):
    """Get single video details"""
    try:
        video = VideoDownload.objects.get(id=video_id)
        return JsonResponse({
            "id": video.id,
            "url": video.url,
            "title": video.title,
            "original_title": video.original_title,
            "description": video.description,
            "original_description": video.original_description,
            "cover_url": video.cover_url,
            "video_url": video.video_url,
            "status": video.status,
            "transcription_status": video.transcription_status,
            "transcript": video.transcript,
            "transcript_hindi": video.transcript_hindi,
            "transcript_language": video.transcript_language,
            "ai_processing_status": video.ai_processing_status,
            "ai_summary": video.ai_summary,
            "ai_tags": video.ai_tags,
            "is_downloaded": video.is_downloaded,
            "extraction_method": video.extraction_method,
            "created_at": video.created_at.isoformat(),
        })
    except VideoDownload.DoesNotExist:
        return JsonResponse({"error": "Video not found"}, status=404)
