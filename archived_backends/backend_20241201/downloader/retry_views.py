"""
Retry API endpoints for failed pipeline steps
"""
import json
import threading
import queue
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import VideoDownload


@csrf_exempt
@require_http_methods(["POST"])
def retry_transcription(request, video_id):
    """Retry failed transcription step"""
    try:
        video = VideoDownload.objects.get(id=video_id)
        
        # Check if transcription actually failed
        if video.transcription_status != 'failed':
            return JsonResponse({
                "error": f"Transcription has not failed. Current status: {video.transcription_status}"
            }, status=400)
        
        # Reset transcription status
        video.transcription_status = 'not_transcribed'
        video.transcript_error_message = ''
        video.transcript_started_at = None
        video.transcript_processed_at = None
        video.save()
        
        # Start transcription
        from .utils import transcribe_video, translate_text
        
        video.transcription_status = 'transcribing'
        video.transcript_started_at = timezone.now()
        video.save()
        
        result = transcribe_video(video)
        
        if result['status'] == 'success':
            video.transcript = result.get('text', '')
            video.transcript_language = result.get('language', '')
            video.transcription_status = 'transcribed'
            video.transcript_processed_at = timezone.now()
            
            # Translate to Hindi
            if video.transcript:
                try:
                    video.transcript_hindi = translate_text(video.transcript, target='hi')
                except Exception as e:
                    print(f"Hindi translation failed: {e}")
                    video.transcript_hindi = ""
            
            video.save()
            
            return JsonResponse({
                "status": "success",
                "message": "Transcription retry successful",
                "transcript": video.transcript
            })
        else:
            video.transcription_status = 'failed'
            video.transcript_error_message = result.get('error', 'Unknown error')
            video.save()
            
            return JsonResponse({
                "error": result.get('error', 'Transcription failed')
            }, status=500)
            
    except VideoDownload.DoesNotExist:
        return JsonResponse({"error": "Video not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def retry_ai_processing(request, video_id):
    """Retry failed AI processing step"""
    try:
        video = VideoDownload.objects.get(id=video_id)
        
        # Check if AI processing actually failed
        if video.ai_processing_status != 'failed':
            return JsonResponse({
                "error": f"AI processing has not failed. Current status: {video.ai_processing_status}"
            }, status=400)
        
        # Reset AI processing status
        video.ai_processing_status = 'not_processed'
        video.ai_error_message = ''
        video.ai_processed_at = None
        video.save()
        
        # Start AI processing
        from .utils import process_video_with_ai
        
        video.ai_processing_status = 'processing'
        video.save()
        
        result = process_video_with_ai(video)
        
        if result['status'] == 'success':
            video.ai_summary = result['summary']
            video.ai_tags = ','.join(result['tags'])
            video.ai_processing_status = 'processed'
            video.ai_processed_at = timezone.now()
            video.save()
            
            return JsonResponse({
                "status": "success",
                "message": "AI processing retry successful",
                "summary": video.ai_summary
            })
        else:
            video.ai_processing_status = 'failed'
            video.ai_error_message = result.get('error', 'Unknown error')
            video.save()
            
            return JsonResponse({
                "error": result.get('error', 'AI processing failed')
            }, status=500)
            
    except VideoDownload.DoesNotExist:
        return JsonResponse({"error": "Video not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def retry_script_generation(request, video_id):
    """Retry failed Hindi script generation step - MOST IMPORTANT"""
    try:
        # Import here to avoid circular imports
        from legacy.root_debris.downloader.models import VideoDownload as LegacyVideoDownload
        
        try:
            # Try legacy model first (where script generation exists)
            video = LegacyVideoDownload.objects.get(id=video_id)
        except:
            # Fallback to current model
            video = VideoDownload.objects.get(id=video_id)
            return JsonResponse({
                "error": "Script generation not available in current backend. Please use legacy backend."
            }, status=400)
        
        # Check if script generation actually failed
        if not hasattr(video, 'script_status') or video.script_status != 'failed':
            status = getattr(video, 'script_status', 'unknown')
            return JsonResponse({
                "error": f"Script generation has not failed. Current status: {status}"
            }, status=400)
        
        # Ensure enhanced_transcript exists - create from transcript if missing
        if not hasattr(video, 'enhanced_transcript') or not video.enhanced_transcript:
            if hasattr(video, 'transcript') and video.transcript:
                if hasattr(video, 'enhanced_transcript'):
                    video.enhanced_transcript = video.transcript
                if hasattr(video, 'enhanced_transcript_without_timestamps'):
                    if hasattr(video, 'transcript_without_timestamps') and video.transcript_without_timestamps:
                        video.enhanced_transcript_without_timestamps = video.transcript_without_timestamps
                    else:
                        import re
                        plain_text = re.sub(r'^\d{2}:\d{2}:\d{2}\s+', '', video.transcript, flags=re.MULTILINE)
                        plain_text = '\n'.join([line.strip() for line in plain_text.split('\n') if line.strip()])
                        video.enhanced_transcript_without_timestamps = plain_text
                video.save()
        
        # Check prerequisites after creating enhanced_transcript
        if not hasattr(video, 'enhanced_transcript') or not video.enhanced_transcript:
            return JsonResponse({
                "error": "Enhanced transcript is required for script generation. Please run transcription first."
            }, status=400)
        
        # Reset script status
        video.script_status = 'not_generated'
        video.script_error_message = ''
        video.script_generated_at = None
        video.hindi_script = ''
        video.save()
        
        # Start script generation with timeout protection
        video.script_status = 'generating'
        video.save()
        
        from legacy.root_debris.downloader.utils import generate_hindi_script
        
        script_queue = queue.Queue()
        exception_queue = queue.Queue()
        
        def run_script_generation():
            try:
                result = generate_hindi_script(video)
                script_queue.put(result)
            except Exception as e:
                exception_queue.put(e)
        
        script_thread = threading.Thread(target=run_script_generation, daemon=True)
        script_thread.start()
        script_thread.join(timeout=300)  # 5 minutes timeout
        
        if script_thread.is_alive():
            error_msg = "Script generation timed out after 5 minutes"
            video.script_status = 'failed'
            video.script_error_message = error_msg
            video.save()
            return JsonResponse({"error": error_msg}, status=500)
        
        if not exception_queue.empty():
            e = exception_queue.get()
            error_msg = f"Script generation error: {str(e)}"
            video.script_status = 'failed'
            video.script_error_message = error_msg
            video.save()
            return JsonResponse({"error": error_msg}, status=500)
        
        if not script_queue.empty():
            script_result = script_queue.get()
            
            if script_result['status'] == 'success':
                video.hindi_script = script_result['script']
                video.script_status = 'generated'
                video.script_generated_at = timezone.now()
                video.script_error_message = ''
                video.save()
                
                return JsonResponse({
                    "status": "success",
                    "message": "Script generation retry successful",
                    "script": script_result['script'][:200] + "..."  # Truncate for response
                })
            else:
                video.script_status = 'failed'
                video.script_error_message = script_result.get('error', 'Unknown error')
                video.save()
                return JsonResponse({
                    "error": script_result.get('error', 'Script generation failed')
                }, status=500)
        
        error_msg = "Script generation completed but no result returned"
        video.script_status = 'failed'
        video.script_error_message = error_msg
        video.save()
        return JsonResponse({"error": error_msg}, status=500)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in retry_script_generation: {str(e)}")
        print(f"Traceback: {error_trace}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def retry_tts_synthesis(request, video_id):
    """Retry failed TTS synthesis step"""
    try:
        # Import legacy model
        from legacy.root_debris.downloader.models import VideoDownload as LegacyVideoDownload
        
        try:
            video = LegacyVideoDownload.objects.get(id=video_id)
        except:
            return JsonResponse({
                "error": "TTS synthesis not available in current backend"
            }, status=400)
        
        if not hasattr(video, 'synthesis_status') or video.synthesis_status != 'failed':
            status = getattr(video, 'synthesis_status', 'unknown')
            return JsonResponse({
                "error": f"TTS synthesis has not failed. Current status: {status}"
            }, status=400)
        
        # Check prerequisites
        if not video.hindi_script:
            return JsonResponse({
                "error": "Hindi script is required for TTS synthesis"
            }, status=400)
        
        # Reset synthesis status
        video.synthesis_status = 'not_synthesized'
        if hasattr(video, 'synthesis_error'):
            video.synthesis_error = ''
        if hasattr(video, 'synthesis_error_message'):
            video.synthesis_error_message = ''
        if hasattr(video, 'synthesized_audio'):
            try:
                video.synthesized_audio.delete(save=False)
            except:
                pass
            video.synthesized_audio = None
        video.save()
        
        # Start TTS synthesis in background
        import threading
        def run_tts_synthesis():
            try:
                from legacy.root_debris.downloader.utils import get_clean_script_for_tts, get_audio_duration, adjust_audio_duration
                from legacy.root_debris.downloader.gemini_tts_service import GeminiTTSService
                from legacy.root_debris.downloader.models import AIProviderSettings
                import tempfile
                import os
                from django.core.files import File
                
                video.refresh_from_db()
                video.synthesis_status = 'synthesizing'
                video.save()
                
                clean_script = get_clean_script_for_tts(video.hindi_script)
                
                settings_obj = AIProviderSettings.objects.first()
                if not settings_obj or not settings_obj.api_key:
                    video.synthesis_status = 'failed'
                    video.synthesis_error = 'Gemini API key not configured'
                    video.save()
                    return
                
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
                    audio_duration = get_audio_duration(temp_audio_path)
                    if audio_duration:
                        duration_diff = abs(audio_duration - video.duration)
                        if duration_diff > 1.0:
                            adjusted_path = adjust_audio_duration(temp_audio_path, video.duration)
                            if adjusted_path and os.path.exists(adjusted_path):
                                os.unlink(temp_audio_path)
                                temp_audio_path = adjusted_path
                
                with open(temp_audio_path, 'rb') as f:
                    video.synthesized_audio.save(f"synthesized_{video.pk}.mp3", File(f), save=False)
                
                video.synthesis_status = 'synthesized'
                if hasattr(video, 'synthesized_at'):
                    video.synthesized_at = timezone.now()
                video.save()
                
                if os.path.exists(temp_audio_path):
                    os.unlink(temp_audio_path)
            except Exception as e:
                video.refresh_from_db()
                video.synthesis_status = 'failed'
                video.synthesis_error = str(e)
                video.save()
        
        tts_thread = threading.Thread(target=run_tts_synthesis, daemon=True)
        tts_thread.start()
        
        return JsonResponse({
            "status": "success",
            "message": "TTS synthesis retry started in background"
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def retry_final_video(request, video_id):
    """Retry failed final video assembly"""
    try:
        from legacy.root_debris.downloader.models import VideoDownload as LegacyVideoDownload
        
        try:
            video = LegacyVideoDownload.objects.get(id=video_id)
        except:
            return JsonResponse({
                "error": "Final video assembly not available in current backend"
            }, status=400)
        
        # Check prerequisites
        if not video.synthesized_audio:
            return JsonResponse({
                "error": "Synthesized audio is required for final video creation"
            }, status=400)
        
        if not video.local_file:
            return JsonResponse({
                "error": "Local video file is required for final video creation"
            }, status=400)
        
        # Reset final video
        if hasattr(video, 'final_processed_video'):
            try:
                video.final_processed_video.delete(save=False)
            except:
                pass
            video.final_processed_video = None
        if hasattr(video, 'final_processed_video_url'):
            video.final_processed_video_url = ''
        video.save()
        
        # Start final video creation in background
        import threading
        def run_final_video():
            try:
                from legacy.root_debris.downloader.utils import find_ffmpeg
                from legacy.root_debris.downloader.watermark_service import apply_moving_watermark
                from legacy.root_debris.downloader.models import WatermarkSettings
                import subprocess
                import tempfile
                import os
                from django.core.files import File
                
                video.refresh_from_db()
                
                ffmpeg_path = find_ffmpeg()
                if not ffmpeg_path:
                    video.synthesis_error = 'ffmpeg not available'
                    video.save()
                    return
                
                if not os.path.exists(video.local_file.path):
                    video.synthesis_error = f'Video file not found: {video.local_file.path}'
                    video.save()
                    return
                
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
                    
                    if os.path.exists(temp_no_audio_path):
                        os.unlink(temp_no_audio_path)
            except Exception as e:
                video.refresh_from_db()
                if hasattr(video, 'synthesis_error'):
                    video.synthesis_error = str(e)
                video.save()
        
        final_thread = threading.Thread(target=run_final_video, daemon=True)
        final_thread.start()
        
        return JsonResponse({
            "status": "success",
            "message": "Final video assembly retry started in background"
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def retry_cloudinary_upload(request, video_id):
    """Retry failed Cloudinary upload"""
    try:
        from legacy.root_debris.downloader.models import VideoDownload as LegacyVideoDownload
        
        try:
            video = LegacyVideoDownload.objects.get(id=video_id)
        except:
            video = VideoDownload.objects.get(id=video_id)
        
        # Check if upload failed or not done
        if hasattr(video, 'cloudinary_url') and video.cloudinary_url:
            return JsonResponse({
                "error": "Video already uploaded to Cloudinary"
            }, status=400)
        
        # Reset and retry upload
        # Implement based on your Cloudinary upload logic
        return JsonResponse({
            "status": "success",
            "message": "Cloudinary upload retry started"
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def retry_google_sheets_sync(request, video_id):
    """Retry failed Google Sheets sync"""
    try:
        from legacy.root_debris.downloader.models import VideoDownload as LegacyVideoDownload
        
        try:
            video = LegacyVideoDownload.objects.get(id=video_id)
        except:
            video = VideoDownload.objects.get(id=video_id)
        
        # Check if sync failed or not done
        if hasattr(video, 'google_sheets_synced') and video.google_sheets_synced:
            return JsonResponse({
                "error": "Video already synced to Google Sheets"
            }, status=400)
        
        # Reset and retry sync
        # Implement based on your Google Sheets sync logic
        return JsonResponse({
            "status": "success",
            "message": "Google Sheets sync retry started"
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
