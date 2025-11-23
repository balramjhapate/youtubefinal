import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import VideoDownload
from .utils import perform_extraction, extract_video_id, translate_text, generate_audio_prompt

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
@require_http_methods(["POST"])
def generate_audio_prompt_view(request):
    """Generate audio prompt for a video using configured AI provider"""
    try:
        data = json.loads(request.body.decode('utf-8'))
        video_id = data.get('video_id')
        
        if not video_id:
            return JsonResponse({"error": "Video ID is required"}, status=400)
        
        try:
            video = VideoDownload.objects.get(pk=video_id)
        except VideoDownload.DoesNotExist:
            return JsonResponse({"error": "Video not found"}, status=404)
        
        # Generate prompt
        result = generate_audio_prompt(video)
        
        if result['status'] == 'success':
            # Save the generated prompt to database
            from django.utils import timezone
            video.audio_prompt_status = 'generated'
            video.audio_generation_prompt = result['prompt']
            video.audio_prompt_generated_at = timezone.now()
            video.audio_prompt_error = ''  # Clear any previous errors
            video.save()
            
            return JsonResponse({
                "prompt": result['prompt'],
                "status": "success"
            })
        else:
            # Save error to database
            video.audio_prompt_status = 'failed'
            video.audio_prompt_error = result.get('error', 'Unknown error')
            video.save()
            
            return JsonResponse({
                "error": result.get('error', 'Unknown error'),
                "status": "failed"
            }, status=400)
            
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


from .models import VoiceProfile
from .voice_cloning import get_voice_cloning_service

@csrf_exempt
@require_http_methods(["GET", "POST"])
def voice_profiles_view(request):
    """Manage voice profiles."""
    if request.method == "GET":
        profiles = VoiceProfile.objects.all()
        data = [{
            "id": p.id,
            "name": p.name,
            "reference_text": p.reference_text,
            "created_at": p.created_at.isoformat()
        } for p in profiles]
        return JsonResponse({"profiles": data})
        
    else:  # POST - Create new profile
        try:
            name = request.POST.get('name')
            ref_text = request.POST.get('reference_text')
            audio_file = request.FILES.get('reference_audio')
            
            if not all([name, ref_text, audio_file]):
                return JsonResponse({"error": "Missing required fields"}, status=400)
                
            profile = VoiceProfile.objects.create(
                name=name,
                reference_text=ref_text,
                reference_audio=audio_file
            )
            
            # Pre-calculate embedding (optional, can be done async)
            try:
                service = get_voice_cloning_service()
                # service.clone_voice(profile.reference_audio.path, profile.reference_text)
                pass
            except Exception as e:
                print(f"Warning: Failed to pre-calculate embedding: {e}")
                
            return JsonResponse({
                "id": profile.id,
                "name": profile.name,
                "status": "created"
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def synthesize_audio_view(request):
    """Synthesize audio from text using a voice profile."""
    try:
        data = json.loads(request.body.decode('utf-8'))
        text = data.get('text')
        profile_id = data.get('profile_id')
        
        if not text or not profile_id:
            return JsonResponse({"error": "Text and profile_id are required"}, status=400)
            
        try:
            profile = VoiceProfile.objects.get(pk=profile_id)
        except VoiceProfile.DoesNotExist:
            return JsonResponse({"error": "Voice profile not found"}, status=404)
            
        service = get_voice_cloning_service()
        output_path = service.synthesize(text, profile)
        
        # Return URL to the generated file
        # Assuming MEDIA_URL is configured
        from django.conf import settings
        relative_path = os.path.relpath(output_path, settings.MEDIA_ROOT)
        audio_url = settings.MEDIA_URL + relative_path
        
        return JsonResponse({
            "audio_url": audio_url,
            "status": "success"
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
