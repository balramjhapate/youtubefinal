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
            
            # Save duration if available
            if video_data.get('duration'):
                download.duration = int(video_data.get('duration'))
            
            download.save()
            
            # Auto-download and process in background
            import threading
            def auto_process():
                try:
                    from .utils import download_file
                    from .utils import transcribe_video
                    # ❌ REMOVED: translate_text, process_video_with_ai - Now handled by frontend
                    from legacy.root_debris.downloader.utils import get_clean_script_for_tts, find_ffmpeg, get_audio_duration, adjust_audio_duration
                    # ❌ REMOVED: generate_hindi_script - Now handled by frontend
                    from legacy.root_debris.downloader.gemini_tts_service import GeminiTTSService
                    from legacy.root_debris.downloader.watermark_service import apply_moving_watermark
                    from legacy.root_debris.downloader.models import WatermarkSettings, AIProviderSettings
                    import subprocess
                    import tempfile
                    import os
                    from django.core.files import File
                    
                    # Refresh video object
                    download.refresh_from_db()
                    
                    # Step 1: Download video
                    print(f"🔄 Auto-processing: Downloading video {download.id}...")
                    if download.video_url and not download.is_downloaded:
                        file_content = download_file(download.video_url)
                        if file_content:
                            filename = f"{download.video_id or 'video'}_{download.pk}.mp4"
                            download.local_file.save(filename, file_content, save=True)
                            download.is_downloaded = True
                            download.save()
                            print(f"✓ Video downloaded: {filename}")
                        else:
                            print(f"✗ Failed to download video")
                            return
                    
                    # Step 2: Transcribe
                    # NOTE: Translation, AI Processing, and Script Generation are now handled by frontend
                    # See: frontend/src/pages/VideoDetail.jsx for auto-processing logic
                    if not download.transcript or download.transcription_status != 'transcribed':
                        print(f"🔄 Auto-processing: Transcribing video {download.id}...")
                        download.transcription_status = 'transcribing'
                        download.transcript_started_at = timezone.now()
                        download.save()
                        
                        result = transcribe_video(download)
                        
                        if result.get('status') == 'success':
                            download.transcript = result.get('text', '')
                            download.transcript_language = result.get('language', '')
                            download.transcription_status = 'transcribed'
                            download.transcript_processed_at = timezone.now()
                            
                            # ❌ REMOVED: Translation is now handled by frontend
                            # Frontend will automatically translate transcript after transcription completes
                            # See: frontend/src/pages/VideoDetail.jsx - Auto-translate useEffect
                            
                            download.save()
                            print(f"✓ Transcription completed")
                            print(f"ℹ️  Translation, AI processing, and script generation will be handled by frontend")
                        else:
                            download.transcription_status = 'failed'
                            download.transcript_error_message = result.get('error', 'Unknown error')
                            download.save()
                            print(f"✗ Transcription failed")
                            return
                    
                    # ❌ REMOVED: Step 3 - AI Processing
                    # AI Processing is now handled by frontend for faster processing
                    # See: frontend/src/pages/VideoDetail.jsx - Auto AI processing useEffect
                    # See: frontend/src/services/aiProcessing.js
                    print(f"ℹ️  AI processing will be handled by frontend (faster, parallel processing)")
                    
                    # ❌ REMOVED: Step 4 - Script Generation
                    # Script Generation is now handled by frontend for faster processing
                    # See: frontend/src/pages/VideoDetail.jsx - Auto script generation useEffect
                    # See: frontend/src/services/scriptGenerator.js
                    print(f"ℹ️  Script generation will be handled by frontend (faster, parallel processing)")
                    
                    # ❌ REMOVED: Step 5 - TTS Synthesis and Step 6 - Final Video Processing
                    # TTS Synthesis and Video Processing will happen after frontend generates script
                    # Use synthesize_audio_view() endpoint for TTS synthesis
                    # Use reprocess_video() endpoint for final video processing
                    print(f"ℹ️  TTS synthesis and video processing can be triggered manually after script generation")
                
                except Exception as e:
                    import traceback
                    print(f"✗ Auto-processing error: {str(e)}")
                    traceback.print_exc()
                    download.refresh_from_db()
                    if download.transcription_status == 'transcribing':
                        download.transcription_status = 'failed'
                        download.transcript_error_message = str(e)
                        download.save()
            
            # Start auto-processing in background
            process_thread = threading.Thread(target=auto_process, daemon=True)
            process_thread.start()
            
            return JsonResponse({
                "video_url": download.video_url,
                "title": download.title,
                "cover_url": download.cover_url,
                "method": download.extraction_method,
                "id": download.id,
                "auto_processing": True,
                "message": "Video extracted. Auto-processing started in background."
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
        from .utils import transcribe_video
        # ❌ REMOVED: translate_text - Translation is now handled by frontend
        
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
            
            # ❌ REMOVED: Translation is now handled by frontend
            # Frontend will automatically translate transcript after transcription completes
            # See: frontend/src/pages/VideoDetail.jsx - Auto-translate useEffect
            # See: frontend/src/services/translation.js
            
            video.save()
            return JsonResponse({
                "status": "success",
                "message": "Transcription completed. Translation will be handled by frontend.",
                "transcript": video.transcript,
                "transcript_hindi": video.transcript_hindi or "",  # May be empty if frontend hasn't translated yet
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
    """
    ⚠️ DEPRECATED: AI processing is now handled by frontend for faster processing.
    
    This endpoint is kept for backward compatibility but will return a deprecation notice.
    Frontend automatically processes videos with AI after transcription completes.
    
    See: frontend/src/pages/VideoDetail.jsx - Auto AI processing useEffect
    See: frontend/src/services/aiProcessing.js
    """
    return JsonResponse({
        "status": "deprecated",
        "message": "AI processing is now handled by frontend. The frontend will automatically process videos with AI after transcription completes.",
        "frontend_location": "frontend/src/pages/VideoDetail.jsx",
        "service_location": "frontend/src/services/aiProcessing.js"
    }, status=410)  # 410 Gone - indicates resource is no longer available

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
    """Synthesize audio using Gemini TTS"""
    try:
        from legacy.root_debris.downloader.gemini_tts_service import GeminiTTSService
        from legacy.root_debris.downloader.utils import get_clean_script_for_tts
        
        # Try to get video from legacy model first (preferred for features)
        video = None
        use_legacy = False
        try:
            from legacy.root_debris.downloader.models import VideoDownload as LegacyVideoDownload
            video = LegacyVideoDownload.objects.get(id=video_id)
            use_legacy = True
        except:
            # Fallback to current model
            video = VideoDownload.objects.get(id=video_id)
        
        # Get script and duration
        script = ""
        duration = 0
        
        if use_legacy:
            script = video.hindi_script
            duration = video.duration
        else:
            script = video.transcript_hindi
            duration = video.duration
            
        if not script:
            return JsonResponse({"error": "No Hindi script available for synthesis"}, status=400)
            
        # Clean script
        clean_script = get_clean_script_for_tts(script)
        if not clean_script:
             return JsonResponse({"error": "Script cleaning failed or resulted in empty text"}, status=400)

        # Update status
        if use_legacy:
            video.synthesis_status = 'synthesizing'
            video.save()
            
        # Initialize TTS service
        tts_service = GeminiTTSService()
        
        # Generate audio
        # Define output path
        import os
        from django.conf import settings
        
        filename = f"tts_{video.video_id or video.id}_{int(timezone.now().timestamp())}.mp3"
        relative_path = f"synthesized_audio/{filename}"
        absolute_path = os.path.join(settings.MEDIA_ROOT, 'synthesized_audio', filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
        
        # Call generate_speech with duration
        tts_service.generate_speech(
            text=clean_script,
            language_code='hi-IN',
            voice_name='Enceladus',
            output_path=absolute_path,
            video_duration=duration
        )
        
        # Update video record
        if use_legacy:
            video.synthesis_status = 'synthesized'
            video.synthesized_audio = relative_path
            video.save()
        
        return JsonResponse({
            "status": "success", 
            "message": "Audio synthesis completed",
            "audio_url": f"{settings.MEDIA_URL}{relative_path}",
            "clean_script": clean_script
        })
        
    except VideoDownload.DoesNotExist:
        return JsonResponse({"error": "Video not found"}, status=404)
    except Exception as e:
        import traceback
        print(f"TTS Error: {str(e)}")
        print(traceback.format_exc())
        
        if 'video' in locals() and video and use_legacy:
            video.synthesis_status = 'failed'
            video.synthesis_error = str(e)
            video.save()
            
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def upload_synthesized_audio_view(request, video_id):
    """
    Upload synthesized audio file from frontend TTS
    Frontend generates audio using Google Gemini TTS API and uploads it here
    """
    try:
        video = VideoDownload.objects.get(id=video_id)
        
        if 'audio' not in request.FILES:
            return JsonResponse({"error": "Audio file is required"}, status=400)
        
        audio_file = request.FILES['audio']
        
        # Save audio file
        import os
        from django.conf import settings
        from django.core.files import File
        
        filename = f"synthesized_{video_id}_{int(timezone.now().timestamp())}.wav"
        
        # Try legacy model first
        use_legacy = False
        try:
            from legacy.root_debris.downloader.models import VideoDownload as LegacyVideoDownload
            legacy_video = LegacyVideoDownload.objects.get(id=video_id)
            use_legacy = True
            video = legacy_video
        except:
            pass
        
        # Save file
        if use_legacy and hasattr(video, 'synthesized_audio'):
            video.synthesized_audio.save(filename, File(audio_file), save=False)
            video.synthesis_status = 'synthesized'
            video.synthesized_at = timezone.now()
            video.save()
        else:
            # For non-legacy model, save to media directory
            relative_path = f"synthesized_audio/{filename}"
            absolute_path = os.path.join(settings.MEDIA_ROOT, 'synthesized_audio', filename)
            os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
            
            with open(absolute_path, 'wb+') as destination:
                for chunk in audio_file.chunks():
                    destination.write(chunk)
            
            # Store path in a custom field or return URL
            # Note: Non-legacy model may not have synthesized_audio field
            # Return the URL for frontend to use
            audio_url = f"{settings.MEDIA_URL}{relative_path}"
        
        return JsonResponse({
            "status": "success",
            "message": "Audio uploaded successfully",
            "audio_url": video.synthesized_audio.url if use_legacy and hasattr(video, 'synthesized_audio') else audio_url
        })
        
    except VideoDownload.DoesNotExist:
        return JsonResponse({"error": "Video not found"}, status=404)
    except Exception as e:
        import traceback
        print(f"Audio upload error: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)

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

@csrf_exempt
@require_http_methods(["POST"])
def update_video_status(request, video_id):
    """Minimal endpoint to update video processing status from frontend"""
    try:
        data = json.loads(request.body.decode('utf-8'))
        video = VideoDownload.objects.get(id=video_id)
        
        # Prepare update fields list for optimized save
        update_fields = []
        
        # Only update fields sent from frontend
        if 'transcript_hindi' in data:
            video.transcript_hindi = data['transcript_hindi']
            update_fields.append('transcript_hindi')
            # Mark transcription as complete if transcript_hindi is provided
            if video.transcription_status != 'transcribed':
                video.transcription_status = 'transcribed'
                update_fields.append('transcription_status')
        
        if 'ai_summary' in data:
            video.ai_summary = data['ai_summary']
            update_fields.append('ai_summary')
            if video.ai_processing_status != 'processed':
                video.ai_processing_status = 'processed'
                update_fields.append('ai_processing_status')
        
        if 'ai_tags' in data:
            video.ai_tags = ','.join(data['ai_tags']) if isinstance(data['ai_tags'], list) else data['ai_tags']
            update_fields.append('ai_tags')
        
        if 'hindi_script' in data:
            video.hindi_script = data['hindi_script']
            update_fields.append('hindi_script')
            # Update script_status if the model has it
            if hasattr(video, 'script_status'):
                video.script_status = 'generated'
                update_fields.append('script_status')
        
        # Note: Audio file uploads should use a separate endpoint
        # See: upload_synthesized_audio_view() for file uploads
        
        # Single optimized database write
        if update_fields:
            video.save(update_fields=update_fields)
        
        return JsonResponse({"status": "updated"}, status=200)
    except VideoDownload.DoesNotExist:
        return JsonResponse({"error": "Video not found"}, status=404)
    except Exception as e:
        import traceback
        print(f"Error updating video status: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def reprocess_video(request, video_id):
    """Reprocess video - run full pipeline: transcription → AI → script → TTS → final video"""
    try:
        import threading
        
        # Try to get video from legacy model first (has more features)
        video = None
        use_legacy = False
        try:
            from legacy.root_debris.downloader.models import VideoDownload as LegacyVideoDownload
            video = LegacyVideoDownload.objects.get(id=video_id)
            use_legacy = True
        except:
            # Fallback to current model
            video = VideoDownload.objects.get(id=video_id)
        
        if not video.is_downloaded and not video.video_url:
            return JsonResponse({
                "error": "Video must be downloaded or have a video URL to reprocess"
            }, status=400)
        
        # Check if video is currently being processed
        if use_legacy:
            if (hasattr(video, 'transcription_status') and video.transcription_status == 'transcribing') or \
               (hasattr(video, 'ai_processing_status') and video.ai_processing_status == 'processing') or \
               (hasattr(video, 'script_status') and video.script_status == 'generating') or \
               (hasattr(video, 'synthesis_status') and video.synthesis_status == 'synthesizing'):
                return JsonResponse({
                    "error": "Video is currently being processed. Please wait for current process to complete."
                }, status=400)
        else:
            if video.transcription_status == 'transcribing' or video.ai_processing_status == 'processing':
                return JsonResponse({
                    "error": "Video is currently being processed. Please wait for current process to complete."
                }, status=400)
        
        # Reset all processing states to start fresh
        if use_legacy:
            # Reset transcription
            if hasattr(video, 'transcription_status'):
                video.transcription_status = 'not_transcribed'
            if hasattr(video, 'transcript'):
                video.transcript = ''
            if hasattr(video, 'transcript_without_timestamps'):
                video.transcript_without_timestamps = ''
            if hasattr(video, 'transcript_hindi'):
                video.transcript_hindi = ''
            if hasattr(video, 'transcript_started_at'):
                video.transcript_started_at = None
            if hasattr(video, 'transcript_processed_at'):
                video.transcript_processed_at = None
            
            # Reset AI processing
            if hasattr(video, 'ai_processing_status'):
                video.ai_processing_status = 'not_processed'
            if hasattr(video, 'ai_summary'):
                video.ai_summary = ''
            if hasattr(video, 'ai_tags'):
                video.ai_tags = ''
            
            # Reset script generation
            if hasattr(video, 'script_status'):
                video.script_status = 'not_generated'
            if hasattr(video, 'hindi_script'):
                video.hindi_script = ''
            
            # Reset TTS synthesis
            if hasattr(video, 'synthesis_status'):
                video.synthesis_status = 'not_synthesized'
            if hasattr(video, 'synthesized_audio'):
                try:
                    video.synthesized_audio.delete(save=False)
                except:
                    pass
                video.synthesized_audio = None
            
            # Reset final video
            if hasattr(video, 'final_processed_video'):
                try:
                    video.final_processed_video.delete(save=False)
                except:
                    pass
                video.final_processed_video = None
            if hasattr(video, 'final_processed_video_url'):
                video.final_processed_video_url = ''
        else:
            # Current model - reset basic fields
            video.transcription_status = 'not_transcribed'
            video.transcript = ''
            video.transcript_hindi = ''
            video.transcript_started_at = None
            video.transcript_processed_at = None
            video.ai_processing_status = 'not_processed'
            video.ai_summary = ''
            video.ai_tags = ''
        
        video.save()
        
        # Run full pipeline in background thread
        def run_full_pipeline():
            try:
                from .utils import transcribe_video
                # ❌ REMOVED: translate_text, process_video_with_ai - Now handled by frontend
                from legacy.root_debris.downloader.utils import get_clean_script_for_tts
                # ❌ REMOVED: generate_hindi_script - Now handled by frontend
                from legacy.root_debris.downloader.gemini_tts_service import GeminiTTSService
                import subprocess
                import tempfile
                import os
                from django.core.files import File
                from django.conf import settings
                
                print(f"🔄 Starting reprocess pipeline for video {video.id}")
                
                # Step 1: Transcription
                video.refresh_from_db()
                video.transcription_status = 'transcribing'
                video.transcript_started_at = timezone.now()
                video.save()
                
                result = transcribe_video(video)
                
                if result.get('status') == 'success':
                    video.transcript = result.get('text', '')
                    video.transcript_language = result.get('language', '')
                    video.transcription_status = 'transcribed'
                    video.transcript_processed_at = timezone.now()
                    
                    # ❌ REMOVED: Translation is now handled by frontend
                    # Frontend will automatically translate transcript after transcription completes
                    # See: frontend/src/pages/VideoDetail.jsx - Auto-translate useEffect
                    
                    video.save()
                    print(f"✓ Step 1: Transcription completed")
                    print(f"ℹ️  Translation, AI processing, and script generation will be handled by frontend")
                    
                    # ❌ REMOVED: Step 2 - AI Processing
                    # AI Processing is now handled by frontend for faster processing
                    # See: frontend/src/pages/VideoDetail.jsx - Auto AI processing useEffect
                    # See: frontend/src/services/aiProcessing.js
                    print(f"ℹ️  AI processing will be handled by frontend (faster, parallel processing)")
                    
                    # ❌ REMOVED: Step 3 - Script Generation
                    # Script Generation is now handled by frontend for faster processing
                    # See: frontend/src/pages/VideoDetail.jsx - Auto script generation useEffect
                    # See: frontend/src/services/scriptGenerator.js
                    print(f"ℹ️  Script generation will be handled by frontend (faster, parallel processing)")
                    
                    # Step 4: TTS Synthesis (only for legacy model)
                    if use_legacy and hasattr(video, 'synthesis_status') and hasattr(video, 'hindi_script') and video.hindi_script:
                        video.refresh_from_db()
                        if video.script_status == 'generated':
                            video.synthesis_status = 'synthesizing'
                            video.save()
                            
                            clean_script = get_clean_script_for_tts(video.hindi_script)
                            
                            # Use Gemini TTS
                            from legacy.root_debris.downloader.models import AIProviderSettings
                            settings_obj = AIProviderSettings.objects.first()
                            if settings_obj and settings_obj.api_key:
                                service = GeminiTTSService(api_key=settings_obj.api_key)
                                
                                temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                                temp_audio_path = temp_audio.name
                                temp_audio.close()
                                
                                service.generate_speech(
                                    text=clean_script,
                                    language_code='hi-IN',
                                    voice_name='Enceladus',
                                    output_path=temp_audio_path,
                                    video_duration=video.duration or 0
                                )
                                
                                # Adjust audio duration to match video
                                if video.duration and os.path.exists(temp_audio_path):
                                    from legacy.root_debris.downloader.utils import get_audio_duration, adjust_audio_duration
                                    audio_duration = get_audio_duration(temp_audio_path)
                                    if audio_duration:
                                        duration_diff = abs(audio_duration - video.duration)
                                        if duration_diff > 1.0:  # More than 1 second difference
                                            print(f"Adjusting TTS audio duration: {audio_duration:.2f}s -> {video.duration:.2f}s")
                                            adjusted_path = adjust_audio_duration(temp_audio_path, video.duration)
                                            if adjusted_path and os.path.exists(adjusted_path):
                                                os.unlink(temp_audio_path)
                                                temp_audio_path = adjusted_path
                                                print(f"✓ Audio duration adjusted to match video")
                                    
                                    with open(temp_audio_path, 'rb') as f:
                                        video.synthesized_audio.save(f"synthesized_{video.pk}.mp3", File(f), save=False)
                                    
                                    video.synthesis_status = 'synthesized'
                                    video.synthesized_at = timezone.now()
                                    video.save()
                                    
                                    if os.path.exists(temp_audio_path):
                                        os.unlink(temp_audio_path)
                                    
                                    print(f"✓ Step 4: TTS synthesis completed")
                            else:
                                video.synthesis_status = 'failed'
                                video.synthesis_error = 'Gemini API key not configured'
                                video.save()
                                print(f"✗ Step 4: TTS synthesis failed - API key not configured")
                    
                    # Step 5: Final Video (only for legacy model)
                    if use_legacy and hasattr(video, 'synthesis_status') and video.synthesis_status == 'synthesized' and video.synthesized_audio and video.local_file:
                        video.refresh_from_db()
                        
                        # Use ffmpeg to remove audio and combine with TTS
                        from legacy.root_debris.downloader.utils import find_ffmpeg
                        ffmpeg_path = find_ffmpeg()
                        
                        if ffmpeg_path and os.path.exists(video.local_file.path):
                            # Remove audio
                            temp_no_audio = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                            temp_no_audio_path = temp_no_audio.name
                            temp_no_audio.close()
                            
                            cmd = [
                                ffmpeg_path,
                                '-i', video.local_file.path,
                                '-c:v', 'copy',
                                '-an',
                                '-y',
                                temp_no_audio_path
                            ]
                            
                            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                            
                            if result.returncode == 0 and os.path.exists(temp_no_audio_path):
                                # Combine with TTS audio
                                temp_final = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                                temp_final_path = temp_final.name
                                temp_final.close()
                                
                                cmd = [
                                    ffmpeg_path,
                                    '-i', temp_no_audio_path,
                                    '-i', video.synthesized_audio.path,
                                    '-c:v', 'copy',
                                    '-c:a', 'aac',
                                    '-map', '0:v:0',
                                    '-map', '1:a:0',
                                    '-shortest',
                                    '-y',
                                    temp_final_path
                                ]
                                
                                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                                
                                if result.returncode == 0 and os.path.exists(temp_final_path):
                                    # Apply watermark if enabled
                                    watermark_applied = False
                                    try:
                                        from legacy.root_debris.downloader.models import WatermarkSettings
                                        from legacy.root_debris.downloader.watermark_service import apply_moving_watermark
                                        
                                        watermark_settings = WatermarkSettings.objects.first()
                                        if watermark_settings and watermark_settings.enabled and watermark_settings.watermark_text:
                                            temp_watermarked = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                                            temp_watermarked_path = temp_watermarked.name
                                            temp_watermarked.close()
                                            
                                            if apply_moving_watermark(
                                                video_path=temp_final_path,
                                                watermark_text=watermark_settings.watermark_text,
                                                output_path=temp_watermarked_path,
                                                position_change_interval=watermark_settings.position_change_interval,
                                                opacity=watermark_settings.opacity,
                                                font_size=watermark_settings.font_size,
                                                font_color=watermark_settings.font_color
                                            ):
                                                os.unlink(temp_final_path)
                                                temp_final_path = temp_watermarked_path
                                                watermark_applied = True
                                                print(f"✓ Watermark applied: '{watermark_settings.watermark_text}'")
                                            else:
                                                if os.path.exists(temp_watermarked_path):
                                                    os.unlink(temp_watermarked_path)
                                    except Exception as e:
                                        print(f"⚠ Watermark error: {e}")
                                    
                                    # Save final video
                                    with open(temp_final_path, 'rb') as f:
                                        video.final_processed_video.save(f"final_{video.pk}.mp4", File(f), save=False)
                                    
                                    if hasattr(video, 'review_status'):
                                        video.review_status = 'pending_review'
                                    video.save()
                                    
                                    if os.path.exists(temp_final_path):
                                        os.unlink(temp_final_path)
                                    
                                    print(f"✓ Step 5: Final video created (watermark: {'yes' if watermark_applied else 'no'})")
                                
                                if os.path.exists(temp_no_audio_path):
                                    os.unlink(temp_no_audio_path)
                else:
                    video.transcription_status = 'failed'
                    video.transcript_error_message = result.get('error', 'Unknown error')
                    video.save()
                    print(f"✗ Transcription failed: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                import traceback
                print(f"Pipeline error during reprocess: {str(e)}")
                traceback.print_exc()
                video.refresh_from_db()
                if hasattr(video, 'transcription_status') and video.transcription_status == 'transcribing':
                    video.transcription_status = 'failed'
                    video.transcript_error_message = str(e)
                video.save()
        
        # Start pipeline in background thread
        pipeline_thread = threading.Thread(target=run_full_pipeline, daemon=True)
        pipeline_thread.start()
        
        return JsonResponse({
            "status": "processing_started",
            "message": "Reprocessing started in background",
            "video_id": video.id
        })
        
    except VideoDownload.DoesNotExist:
        return JsonResponse({"error": "Video not found"}, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)
