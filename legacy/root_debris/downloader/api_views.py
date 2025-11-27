"""
REST API Views for RedNote Downloader
"""
import os
from django.utils import timezone
from django.db.models import Count, Q
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import VideoDownload, AIProviderSettings
from .serializers import (
    VideoDownloadSerializer, VideoDownloadListSerializer,
    AIProviderSettingsSerializer, VideoExtractSerializer,
    VideoTranscribeSerializer, BulkActionSerializer, DashboardStatsSerializer
)
from .utils import (
    perform_extraction, extract_video_id, detect_video_source, translate_text,
    transcribe_video, download_file,
    process_video_with_ai, get_video_duration,
    calculate_tts_parameters, generate_hindi_script
)


class VideoDownloadViewSet(viewsets.ModelViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    """
    ViewSet for Video Downloads - handles all CRUD operations
    """
    queryset = VideoDownload.objects.all().order_by('-created_at')
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        """Get queryset"""
        return VideoDownload.objects.all().order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return VideoDownloadListSerializer
        return VideoDownloadSerializer
    
    def get_serializer_context(self):
        """Add request to serializer context for building absolute URLs"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def list(self, request):
        """List all videos with optional filtering"""
        queryset = self.get_queryset()

        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by transcription status
        transcription_status = request.query_params.get('transcription_status')
        if transcription_status:
            queryset = queryset.filter(transcription_status=transcription_status)

        # Filter by AI processing status
        ai_status = request.query_params.get('ai_processing_status')
        if ai_status:
            queryset = queryset.filter(ai_processing_status=ai_status)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def extract(self, request):
        """Extract video from URL or handle local file upload"""
        # Check if it's a file upload
        if 'file' in request.FILES:
            return self._handle_local_upload(request)
        
        serializer = VideoExtractSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        url = serializer.validated_data.get('url')
        
        if not url:
            return Response({
                "error": "URL is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Detect video source
        video_source = detect_video_source(url) if url else 'local'
        
        # Check for existing video by ID
        video_id = extract_video_id(url, source=video_source) if url else None
        
        # For YouTube Shorts, ensure we have a valid video_id
        if video_source == 'youtube' and not video_id:
            return Response({
                "error": "Could not extract video ID from YouTube URL. Please check the URL format."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if video_id:
            existing = VideoDownload.objects.filter(video_id=video_id).first()
            if existing:
                if existing.status == 'success':
                    return Response({
                        "id": existing.id,
                        "video_url": existing.video_url,
                        "title": existing.title,
                        "cover_url": existing.cover_url,
                        "method": existing.extraction_method,
                        "source": existing.video_source,
                        "cached": True
                    })
                else:
                    # If previous extraction failed, delete the old record and try again
                    print(f"Previous extraction failed for video_id {video_id}, deleting and retrying...")
                    existing.delete()

        # Create pending download record
        try:
            download = VideoDownload.objects.create(
                url=url,
                video_id=video_id,
                video_source=video_source,
                status='pending'
            )
        except Exception as e:
            error_str = str(e).lower()
            if 'video_id' in error_str or 'unique constraint' in error_str or 'unique' in error_str:
                # Video already exists, try to get it
                if video_id:
                    existing = VideoDownload.objects.filter(video_id=video_id).first()
                    if existing:
                        if existing.status == 'success':
                            return Response({
                                "id": existing.id,
                                "video_url": existing.video_url,
                                "title": existing.title,
                                "cover_url": existing.cover_url,
                                "method": existing.extraction_method,
                                "source": existing.video_source,
                                "cached": True
                            })
                        else:
                            # Update existing failed record
                            download = existing
                            download.status = 'pending'
                            download.url = url
                            download.save()
                    else:
                        return Response({
                            "error": f"Video with ID '{video_id}' already exists."
                        }, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({
                        "error": "Could not create video record. Please try again."
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                print(f"Error creating video record: {e}")
                import traceback
                traceback.print_exc()
                return Response({
                    "error": f"Error creating video record: {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Perform extraction with error handling
        try:
            video_data = perform_extraction(url)
        except Exception as e:
            print(f"Error during extraction: {e}")
            import traceback
            traceback.print_exc()
            download.status = 'failed'
            download.error_message = f"Extraction error: {str(e)}"
            download.save()
            return Response({
                "error": f"Extraction failed: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if video_data:
            try:
                download.status = 'success'
                download.extraction_method = video_data.get('method', '')
                download.video_url = video_data.get('video_url', '')
                download.cover_url = video_data.get('cover_url', '')
                
                # Update video_source from extraction result if available
                extracted_source = video_data.get('source', video_source)
                if extracted_source:
                    download.video_source = extracted_source

                # Get original title and description from the platform
                original_title = video_data.get('original_title', '')
                original_desc = video_data.get('original_description', '')
                
                # If original_title is empty, try to get from title
                if not original_title:
                    original_title = video_data.get('title', '')
                if not original_desc:
                    original_desc = video_data.get('description', '')

                download.original_title = original_title
                download.original_description = original_desc
                
                # Only translate if original is not in English (for non-English platforms)
                # For YouTube, Facebook, Instagram, Vimeo - titles are usually already in English
                if download.video_source in ['youtube', 'facebook', 'instagram', 'vimeo']:
                    # Use original title as-is for these platforms
                    download.title = original_title if original_title else video_data.get('title', '')
                    download.description = original_desc if original_desc else video_data.get('description', '')
                else:
                    # Translate for RedNote and other platforms
                    download.title = translate_text(original_title, target='en') if original_title else ''
                    download.description = translate_text(original_desc, target='en') if original_desc else ''
                
                # Get duration from extraction metadata if available
                duration = video_data.get('duration')
                if duration:
                    download.duration = float(duration)
                    print(f"Video duration from extraction metadata: {duration} seconds")
                else:
                    # Try to extract duration from video URL using yt-dlp if available
                    if download.video_url:
                        try:
                            from .utils import extract_video_ytdlp
                            metadata = extract_video_ytdlp(download.video_url)
                            if metadata and metadata.get('duration'):
                                duration = float(metadata.get('duration'))
                                download.duration = duration
                                print(f"Video duration extracted from yt-dlp: {duration} seconds")
                        except Exception as e:
                            print(f"Could not extract duration from video URL: {e}")
                
                # Calculate TTS parameters if duration is available
                if download.duration:
                    from .utils import calculate_tts_parameters
                    tts_params = calculate_tts_parameters(download.duration)
                    download.tts_speed = tts_params['speed']
                    download.tts_temperature = tts_params['temperature']
                    download.tts_repetition_penalty = tts_params['repetition_penalty']
                    print(f"TTS parameters calculated: speed={tts_params['speed']}, temp={tts_params['temperature']}")
                
                download.save()

                return Response({
                    "id": download.id,
                    "video_url": download.video_url,
                    "title": download.title,
                    "cover_url": download.cover_url,
                    "method": download.extraction_method,
                    "source": download.video_source,
                    "cached": False
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                print(f"Error saving video data: {e}")
                import traceback
                traceback.print_exc()
                download.status = 'failed'
                download.error_message = f"Error saving video data: {str(e)}"
                download.save()
                return Response({
                    "error": f"Error saving video data: {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            download.status = 'failed'
            download.error_message = "Could not extract video. The link might be invalid or protected."
            download.save()

            return Response({
                "error": "Could not extract video. The link might be invalid or protected."
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def _handle_local_upload(self, request):
        """Handle local video file upload"""
        try:
            uploaded_file = request.FILES['file']
            title = request.data.get('title', uploaded_file.name)
            
            # Create video record
            download = VideoDownload.objects.create(
                url=None,
                video_id=None,
                video_source='local',
                extraction_method='local',
                status='success',
                title=title,
                original_title=title,
                is_downloaded=True,
            )
            
            # Save uploaded file
            download.local_file = uploaded_file
            download.save()
            
            # Try to get duration
            try:
                if download.local_file:
                    duration = get_video_duration(download.local_file.path)
                    if duration:
                        download.duration = duration
                        # Calculate TTS parameters
                        tts_params = calculate_tts_parameters(duration)
                        download.tts_speed = tts_params['speed']
                        download.tts_temperature = tts_params['temperature']
                        download.tts_repetition_penalty = tts_params['repetition_penalty']
                        download.save()
            except Exception as e:
                print(f"Error getting video duration: {e}")
            
            return Response({
                "id": download.id,
                "title": download.title,
                "source": download.video_source,
                "method": download.extraction_method,
                "file_url": request.build_absolute_uri(download.local_file.url) if download.local_file else None,
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                "error": f"Failed to upload video: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def download(self, request, pk=None):
        """Download video file to local storage"""
        video = self.get_object()

        if video.is_downloaded and video.local_file:
            return Response({
                "status": "already_downloaded",
                "file_url": request.build_absolute_uri(video.local_file.url)
            })

        if not video.video_url:
            return Response({
                "error": "No video URL available"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Check if URL is an HLS stream (M3U playlist)
            is_hls = ('.m3u8' in video.video_url.lower() or 
                     'manifest.googlevideo.com' in video.video_url.lower() or
                     'hls' in video.video_url.lower())
            
            # Track duration from download process
            duration_from_download = None
            file_content = None
            
            if is_hls:
                print(f"Detected HLS stream, using yt-dlp to download: {video.video_url}")
                from .utils import download_video_with_ytdlp
                result = download_video_with_ytdlp(video.video_url)
                if result:
                    if isinstance(result, tuple) and len(result) == 2:
                        file_content, duration_from_download = result
                        print(f"Downloaded with duration: {duration_from_download} seconds")
                    else:
                        file_content = result
            else:
                # Try direct download first
                file_content = download_file(video.video_url)
                
                # If download failed or returned None, try using yt-dlp as fallback
                if not file_content:
                    print(f"Direct download failed, trying yt-dlp for: {video.video_url}")
                    from .utils import download_video_with_ytdlp
                    result = download_video_with_ytdlp(video.video_url)
                    if result:
                        if isinstance(result, tuple) and len(result) == 2:
                            file_content, duration_from_download = result
                            print(f"Downloaded with duration: {duration_from_download} seconds")
                        else:
                            file_content = result
            
            if file_content:
                # Validate file content (not size - can be any size from small clips to large movies like 2GB)
                # Only check if file is extremely small (< 1KB) or has invalid content
                if file_content.size < 1024:
                    return Response({
                        "error": f"Downloaded file is too small ({file_content.size} bytes) to be a video file."
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                # Check file content type (not size - size can be any value)
                file_content.seek(0)
                first_bytes = file_content.read(1000)
                file_content.seek(0)
                
                # Check if it's an M3U playlist (regardless of size)
                if first_bytes.startswith(b'#EXTM3U') or first_bytes.startswith(b'#EXT-X-VERSION'):
                    print(f"ERROR: Downloaded file is an M3U playlist (HLS stream)")
                    print(f"Content: {first_bytes[:500]}")
                    return Response({
                        "error": f"Downloaded file is an M3U playlist (HLS stream), not a video file. Size: {file_content.size} bytes. The video needs to be re-downloaded using yt-dlp."
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                # Check if it's HTML/error page (regardless of size)
                if b'<html' in first_bytes.lower() or b'<!doctype' in first_bytes.lower():
                    print(f"ERROR: Downloaded file is HTML/error page")
                    print(f"Content: {first_bytes[:500]}")
                    return Response({
                        "error": f"Downloaded file appears to be an error page, not a video file. Size: {file_content.size} bytes."
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                # Check for video file signatures (but don't block if not found - ffmpeg will handle format detection)
                video_signatures = [
                    b'\x00\x00\x00 ftyp',  # MP4
                    b'\x1a\x45\xdf\xa3',    # WebM/Matroska
                    b'RIFF',                # AVI/WAV
                    b'\x00\x00\x01\xba',   # MPEG
                    b'\x00\x00\x01\xb3',   # MPEG
                ]
                is_video = any(first_bytes.startswith(sig) for sig in video_signatures)
                
                if not is_video and file_content.size < 10000:
                    # Very small file without video signature - likely invalid
                    print(f"ERROR: Downloaded file does not appear to be a valid video file")
                    print(f"Content: {first_bytes[:500]}")
                    return Response({
                        "error": f"Downloaded file does not appear to be a valid video file. Size: {file_content.size} bytes. Please try re-downloading."
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                if not is_video:
                    print(f"WARNING: File does not have standard video signatures, but size is reasonable ({file_content.size} bytes). Will attempt to save - ffmpeg will handle format detection.")
                
                filename = f"{video.video_id or video.id}.mp4"
                video.local_file.save(filename, file_content)
                video.is_downloaded = True
                
                # Ensure file is saved and flushed before reading
                video.save()
                
                # Extract video duration - ALWAYS extract during download
                duration = None
                
                # Priority 1: Use duration from download process (yt-dlp)
                if duration_from_download:
                    duration = float(duration_from_download)
                    print(f"Video duration from download process: {duration} seconds")
                
                # Priority 2: Try to get duration from yt-dlp metadata if available
                if not duration and video.video_url:
                    if video.video_source == 'youtube' or 'youtube' in video.video_url.lower():
                        try:
                            from .utils import extract_video_ytdlp
                            metadata = extract_video_ytdlp(video.video_url)
                            if metadata and metadata.get('duration'):
                                duration = float(metadata.get('duration'))
                                print(f"Video duration from yt-dlp metadata: {duration} seconds")
                        except Exception as e:
                            print(f"Could not get duration from yt-dlp metadata: {e}")
                
                # Priority 3: Extract from downloaded file using ffprobe
                if not duration:
                    try:
                        video_path = video.local_file.path
                        # Wait a moment to ensure file is fully written
                        import time
                        time.sleep(0.5)
                        
                        duration = get_video_duration(video_path)
                        if duration:
                            print(f"Video duration extracted from file using ffprobe: {duration} seconds")
                    except Exception as e:
                        print(f"Error extracting duration from file: {e}")
                        import traceback
                        traceback.print_exc()
                
                # ALWAYS save duration if found (even if it already exists, update it)
                if duration:
                    video.duration = float(duration)
                    
                    # Calculate TTS parameters based on duration
                    tts_params = calculate_tts_parameters(duration)
                    video.tts_speed = tts_params['speed']
                    video.tts_temperature = tts_params['temperature']
                    video.tts_repetition_penalty = tts_params['repetition_penalty']
                    print(f"✓ Duration saved: {duration} seconds ({int(duration // 60)}:{int(duration % 60):02d})")
                    print(f"TTS parameters calculated: speed={tts_params['speed']}, temp={tts_params['temperature']}")
                else:
                    print("WARNING: Could not extract video duration - duration will not be saved")
                
                video.save()

                return Response({
                    "status": "success",
                    "file_url": request.build_absolute_uri(video.local_file.url),
                    "duration": video.duration,
                    "duration_formatted": f"{int(video.duration // 60)}:{int(video.duration % 60):02d}" if video.duration else None
                })
            else:
                return Response({
                    "error": "Failed to download video. The video URL might be an HLS stream that requires special handling."
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def transcribe(self, request, pk=None):
        """Start transcription, AI processing, and script generation in one automated flow"""
        video = self.get_object()

        if video.transcription_status == 'transcribing':
            return Response({
                "status": "already_processing",
                "message": "Processing is already in progress",
                "current_step": "transcribing"
            })

        if not video.is_downloaded and not video.video_url:
            return Response({
                "error": "Video must be downloaded or have a video URL to transcribe"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Step 1: Transcription
        video.transcription_status = 'transcribing'
        video.transcript_started_at = timezone.now()
        video.save()

        try:
            # Transcribe video
            result = transcribe_video(video)

            if result['status'] == 'success':
                # Save transcript with timestamps AND without timestamps
                video.transcription_status = 'transcribed'
                transcript_text = result.get('text', '')
                timestamped_text = result.get('transcript_with_timestamps', '')
                transcript_without_timestamps = result.get('transcript_without_timestamps', transcript_text)
                srt_text = result.get('srt', '')
                
                # Store transcript WITH timestamps (00:00:00 text format) - this is what user sees
                # IMPORTANT: Store original transcript (may be in Arabic/Urdu/other languages) with timestamps
                if timestamped_text:
                    video.transcript = timestamped_text
                elif srt_text:
                    # Convert SRT to timestamped format
                    from .utils import convert_srt_to_timestamped_text
                    video.transcript = convert_srt_to_timestamped_text(srt_text) or srt_text
                else:
                    video.transcript = transcript_text
                
                # Store transcript WITHOUT timestamps for processing and display
                # Extract plain text from timestamped version if needed
                if transcript_without_timestamps:
                    video.transcript_without_timestamps = transcript_without_timestamps
                elif timestamped_text:
                    # Extract text from timestamped format (remove timestamps)
                    import re
                    plain_text = re.sub(r'^\d{2}:\d{2}:\d{2}\s+', '', timestamped_text, flags=re.MULTILINE)
                    plain_text = '\n'.join([line.strip() for line in plain_text.split('\n') if line.strip()])
                    video.transcript_without_timestamps = plain_text
                else:
                    video.transcript_without_timestamps = transcript_text
                
                # IMPORTANT: Ensure Hindi translation is properly stored
                # If transcript is in Arabic/Urdu, translate it to Hindi
                hindi_transcript = result.get('text_hindi', '')
                if not hindi_transcript and transcript_without_timestamps:
                    # If Hindi translation not provided, translate the plain text
                    from .utils import translate_text
                    print(f"Translating transcript to Hindi (language: {result.get('language', 'unknown')})...")
                    hindi_transcript = translate_text(transcript_without_timestamps, target='hi')
                
                video.transcript_hindi = hindi_transcript
                video.transcript_language = result.get('language', '')
                video.transcript_processed_at = timezone.now()
                video.transcript_error_message = ''
                video.save()

                # Step 2: AI Processing (automatically after transcription)
                try:
                    video.ai_processing_status = 'processing'
                    video.save()
                    
                    ai_result = process_video_with_ai(video)
                    
                    if ai_result['status'] == 'success':
                        video.ai_processing_status = 'processed'
                        video.ai_summary = ai_result.get('summary', '')
                        video.ai_tags = ai_result.get('tags', [])
                        video.ai_processed_at = timezone.now()
                        video.ai_error_message = ''
                        video.save()
                    else:
                        video.ai_processing_status = 'failed'
                        video.ai_error_message = ai_result.get('error', 'Unknown error')
                        video.save()
                except Exception as e:
                    print(f"AI processing error: {e}")
                    video.ai_processing_status = 'failed'
                    video.ai_error_message = str(e)
                    video.save()

                # Step 3: Script Generation (automatically after AI processing)
                try:
                    video.script_status = 'generating'
                    video.save()
                    
                    script_result = generate_hindi_script(video)
                    
                    if script_result['status'] == 'success':
                        video.hindi_script = script_result['script']
                        video.script_status = 'generated'
                        video.script_generated_at = timezone.now()
                        video.script_error_message = ''
                        video.save()
                    else:
                        video.script_status = 'failed'
                        video.script_error_message = script_result.get('error', 'Unknown error')
                        video.save()
                except Exception as e:
                    print(f"Script generation error: {e}")
                    video.script_status = 'failed'
                    video.script_error_message = str(e)
                    video.save()

                # Step 4: TTS Generation (automatically after script generation)
                tts_audio_url = None
                if video.script_status == 'generated' and video.hindi_script:
                    try:
                        video.synthesis_status = 'synthesizing'
                        video.save()
                        
                        from .utils import get_clean_script_for_tts
                        clean_script = get_clean_script_for_tts(video.hindi_script)
                        
                        # Use XTTS service for TTS generation
                        from .xtts_service import XTTSService, TTS_AVAILABLE
                        if TTS_AVAILABLE:
                            service = XTTSService()
                            
                            # Get default voice profile or use a default speaker
                            import tempfile
                            import os
                            temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
                            temp_audio_path = temp_audio.name
                            temp_audio.close()
                            
                            # Use default Hindi speaker or get from voice profile
                            speaker_wav = None
                            if video.voice_profile and video.voice_profile.reference_audio:
                                speaker_wav = video.voice_profile.reference_audio.path
                            
                            if not speaker_wav:
                                # Use default speaker (you may need to provide a default Hindi speaker file)
                                # For now, we'll skip if no voice profile
                                print("No voice profile available, skipping TTS generation")
                                video.synthesis_status = 'failed'
                                video.synthesis_error = 'No voice profile available for TTS'
                                video.save()
                            else:
                                # Generate TTS audio
                                service.generate_speech(
                                    text=clean_script,
                                    speaker_wav_path=speaker_wav,
                                    language='hi',
                                    output_path=temp_audio_path,
                                    speed=video.tts_speed,
                                    temperature=video.tts_temperature,
                                    repetition_penalty=video.tts_repetition_penalty
                                )
                                
                                # Adjust audio duration to match video duration if available
                                if video.duration and os.path.exists(temp_audio_path):
                                    from .utils import get_audio_duration, adjust_audio_duration
                                    audio_duration = get_audio_duration(temp_audio_path)
                                    if audio_duration:
                                        duration_diff = abs(audio_duration - video.duration)
                                        if duration_diff > 0.5:  # If difference is more than 0.5 seconds
                                            print(f"Adjusting TTS audio duration: {audio_duration:.2f}s -> {video.duration:.2f}s")
                                            adjusted_path = adjust_audio_duration(temp_audio_path, video.duration)
                                            if adjusted_path and adjusted_path != temp_audio_path:
                                                # If a new file was created, update temp_audio_path
                                                if os.path.exists(temp_audio_path):
                                                    os.unlink(temp_audio_path)
                                                temp_audio_path = adjusted_path
                                            elif not adjusted_path:
                                                print(f"WARNING: Could not adjust audio duration, using original audio")
                                        else:
                                            print(f"TTS audio duration ({audio_duration:.2f}s) matches video duration ({video.duration:.2f}s)")
                                
                                # Save audio file
                                from django.core.files import File
                                with open(temp_audio_path, 'rb') as f:
                                    video.synthesized_audio.save(f"synthesized_audio_{video.pk}.wav", File(f), save=False)
                                
                                video.synthesis_status = 'synthesized'
                                video.synthesis_error = ''
                                video.save()
                                
                                # Clean up temp file
                                if os.path.exists(temp_audio_path):
                                    os.unlink(temp_audio_path)
                                
                                print(f"TTS audio generated successfully for video {video.pk}")
                        else:
                            print("TTS not available, skipping audio generation")
                            video.synthesis_status = 'failed'
                            video.synthesis_error = 'TTS service not available'
                            video.save()
                    except Exception as e:
                        print(f"TTS generation error: {e}")
                        import traceback
                        traceback.print_exc()
                        video.synthesis_status = 'failed'
                        video.synthesis_error = str(e)
                        video.save()

                # Step 5: Remove audio from video and combine with new TTS audio
                # ALWAYS use ffmpeg - it's more reliable than NCA Toolkit
                final_video_url = None
                voice_removed_url = None
                
                # Check if we have all prerequisites
                if video.synthesis_status == 'synthesized' and video.synthesized_audio:
                    if not video.local_file:
                        print(f"✗ Error: No local video file available for video {video.pk}")
                        video.synthesis_error = "No local video file available for processing"
                        video.save()
                    else:
                        # ALWAYS use ffmpeg - it's more reliable
                        try:
                            from .utils import find_ffmpeg
                            import subprocess
                            import tempfile
                            import os
                            
                            ffmpeg_path = find_ffmpeg()
                            if not ffmpeg_path:
                                print("✗ ffmpeg not found")
                                video.synthesis_error = "ffmpeg not available"
                                video.save()
                            else:
                                video_path = video.local_file.path
                                if not os.path.exists(video_path):
                                    print(f"✗ Video file not found: {video_path}")
                                    video.synthesis_error = f"Video file not found: {video_path}"
                                    video.save()
                                else:
                                    # Step 5a: Remove audio using ffmpeg
                                    print(f"Step 5a (ffmpeg): Removing audio from video {video.pk}...")
                                    temp_no_audio = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                                    temp_no_audio_path = temp_no_audio.name
                                    temp_no_audio.close()
                                    
                                    # Remove audio: -an flag removes audio
                                    cmd = [
                                        ffmpeg_path,
                                        '-i', video_path,
                                        '-c:v', 'copy',  # Copy video codec (no re-encoding)
                                        '-an',  # Remove audio
                                        '-y',  # Overwrite output
                                        temp_no_audio_path
                                    ]
                                    
                                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                                    if result.returncode == 0 and os.path.exists(temp_no_audio_path):
                                        # Save voice-removed video
                                        from django.core.files import File
                                        with open(temp_no_audio_path, 'rb') as f:
                                            video.voice_removed_video.save(f"voice_removed_{video.pk}.mp4", File(f), save=False)
                                        voice_removed_url = request.build_absolute_uri(video.voice_removed_video.url)
                                        video.voice_removed_video_url = voice_removed_url
                                        video.save()
                                        print(f"✓ Step 5a (ffmpeg) completed: Voice removed video saved: {voice_removed_url}")
                                        
                                        # Clean up temp file
                                        os.unlink(temp_no_audio_path)
                                        
                                        # Use the saved file for next step
                                        voice_removed_file_path = video.voice_removed_video.path
                                        
                                        # Step 5b: Combine TTS audio with video
                                        if video.synthesized_audio and os.path.exists(video.synthesized_audio.path):
                                            print(f"Step 5b (ffmpeg): Combining TTS audio with video {video.pk}...")
                                            audio_path = video.synthesized_audio.path
                                            temp_final = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                                            temp_final_path = temp_final.name
                                            temp_final.close()
                                            
                                            # Combine audio and video - ensure proper sync
                                            # Use map to explicitly map streams and ensure sync
                                            cmd = [
                                                ffmpeg_path,
                                                '-i', voice_removed_file_path,
                                                '-i', audio_path,
                                                '-c:v', 'copy',  # Copy video codec (no re-encoding)
                                                '-c:a', 'aac',  # Encode audio as AAC
                                                '-b:a', '192k',  # Audio bitrate
                                                '-map', '0:v:0',  # Map video stream from first input
                                                '-map', '1:a:0',  # Map audio stream from second input
                                                '-shortest',  # Finish when shortest stream ends
                                                '-y',  # Overwrite output
                                                temp_final_path
                                            ]
                                            
                                            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                                            if result.returncode == 0 and os.path.exists(temp_final_path):
                                                # Save final video
                                                with open(temp_final_path, 'rb') as f:
                                                    video.final_processed_video.save(f"final_{video.pk}.mp4", File(f), save=False)
                                                final_video_url = request.build_absolute_uri(video.final_processed_video.url)
                                                video.final_processed_video_url = final_video_url
                                                # Set review status to pending_review
                                                video.review_status = 'pending_review'
                                                video.save()
                                                os.unlink(temp_final_path)
                                                print(f"✓ Step 5b (ffmpeg) completed: Final video with new audio created: {final_video_url}")
                                                print(f"✓ Video set to 'pending_review' status - ready for review")
                                            else:
                                                error_msg = f"ffmpeg combine failed: {result.stderr[:500] if result.stderr else 'Unknown error'}"
                                                print(f"✗ Step 5b (ffmpeg) failed: {error_msg}")
                                                video.synthesis_error = error_msg
                                                video.save()
                                                if os.path.exists(temp_final_path):
                                                    os.unlink(temp_final_path)
                                        else:
                                            error_msg = "Synthesized audio file not found"
                                            print(f"✗ Step 5b (ffmpeg) failed: {error_msg}")
                                            video.synthesis_error = error_msg
                                            video.save()
                                    else:
                                        error_msg = f"ffmpeg remove audio failed: {result.stderr[:500] if result.stderr else 'Unknown error'}"
                                        print(f"✗ Step 5a (ffmpeg) failed: {error_msg}")
                                        video.synthesis_error = error_msg
                                        video.save()
                                        # Clean up temp file on failure
                                        if os.path.exists(temp_no_audio_path):
                                            os.unlink(temp_no_audio_path)
                        except subprocess.TimeoutExpired:
                            error_msg = "ffmpeg processing timed out (exceeded 5 minutes)"
                            print(f"✗ {error_msg}")
                            video.synthesis_error = error_msg
                            video.save()
                        except Exception as e:
                            error_msg = f"ffmpeg processing error: {str(e)}"
                            print(f"✗ {error_msg}")
                            import traceback
                            traceback.print_exc()
                            video.synthesis_error = error_msg
                            video.save()
                else:
                    if video.synthesis_status != 'synthesized':
                        print(f"⚠ TTS not synthesized yet (status: {video.synthesis_status}), skipping audio replacement")
                    if not video.synthesized_audio:
                        print(f"⚠ No synthesized audio available, skipping audio replacement")

                # Refresh video object from database to get latest file URLs
                video.refresh_from_db()
                
                # Use serializer to get properly formatted response with all URLs
                serializer = self.get_serializer(video, context={'request': request})
                serializer_data = serializer.data
                
                # Add additional response data
                serializer_data.update({
                    "status": "success",
                    "transcript_with_timestamps": timestamped_text if timestamped_text else video.transcript,
                    "transcript_without_timestamps": result.get('transcript_without_timestamps', transcript_text),
                })
                
                # Ensure video URLs are included (serializer should handle this, but add explicit checks)
                if not serializer_data.get('voice_removed_video_url') and voice_removed_url:
                    serializer_data['voice_removed_video_url'] = voice_removed_url
                
                if not serializer_data.get('final_processed_video_url') and final_video_url:
                    serializer_data['final_processed_video_url'] = final_video_url
                
                return Response(serializer_data)
            else:
                video.transcription_status = 'failed'
                video.transcript_error_message = result.get('error', 'Unknown error')
                video.save()

                return Response({
                    "status": "failed",
                    "error": result.get('error', 'Unknown error'),
                    "step": "transcription"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            video.transcription_status = 'failed'
            video.transcript_error_message = str(e)
            video.save()

            return Response({
                "status": "failed",
                "error": str(e),
                "step": "transcription"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def transcription_status(self, request, pk=None):
        """Get transcription status for a video"""
        video = self.get_object()

        response_data = {
            "status": video.transcription_status,
            "transcript": video.transcript if video.transcription_status == 'transcribed' else None,
            "transcript_hindi": video.transcript_hindi if video.transcription_status == 'transcribed' else None,
            "language": video.transcript_language if video.transcription_status == 'transcribed' else None,
            "error": video.transcript_error_message if video.transcription_status == 'failed' else None,
        }

        if video.transcription_status == 'transcribing' and video.transcript_started_at:
            elapsed = (timezone.now() - video.transcript_started_at).total_seconds()
            response_data['elapsed_seconds'] = int(elapsed)

        return Response(response_data)

    @action(detail=True, methods=['post'])
    def process_ai(self, request, pk=None):
        """Process video with AI"""
        video = self.get_object()

        if video.ai_processing_status == 'processing':
            return Response({
                "status": "already_processing",
                "message": "AI processing is already in progress"
            })

        if video.ai_processing_status == 'processed':
            return Response({
                "status": "already_processed",
                "summary": video.ai_summary,
                "tags": video.ai_tags
            })

        video.ai_processing_status = 'processing'
        video.save()

        try:
            result = process_video_with_ai(video)

            if result['status'] == 'success':
                video.ai_processing_status = 'processed'
                video.ai_summary = result.get('summary', '')
                video.ai_tags = result.get('tags', '')
                video.ai_processed_at = timezone.now()
                video.ai_error_message = ''
                video.save()

                return Response({
                    "status": "success",
                    "summary": video.ai_summary,
                    "tags": video.ai_tags
                })
            else:
                video.ai_processing_status = 'failed'
                video.ai_error_message = result.get('error', 'Unknown error')
                video.save()

                return Response({
                    "status": "failed",
                    "error": result.get('error', 'Unknown error')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            video.ai_processing_status = 'failed'
            video.ai_error_message = str(e)
            video.save()

            return Response({
                "status": "failed",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """Update review status of final processed video"""
        video = self.get_object()
        
        if not video.final_processed_video:
            return Response({
                "error": "No final processed video available for review"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        review_status = request.data.get('review_status')
        review_notes = request.data.get('review_notes', '')
        
        if review_status not in ['approved', 'needs_revision', 'rejected']:
            return Response({
                "error": "Invalid review_status. Must be one of: approved, needs_revision, rejected"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        video.review_status = review_status
        video.review_notes = review_notes
        video.reviewed_at = timezone.now()
        video.save()
        
        return Response({
            "status": "success",
            "review_status": video.review_status,
            "review_notes": video.review_notes,
            "reviewed_at": video.reviewed_at
        })

    @action(detail=True, methods=['post'])
    def reprocess(self, request, pk=None):
        """Reprocess video - reset processing state and re-run the full pipeline"""
        video = self.get_object()
        
        if not video.is_downloaded and not video.video_url:
            return Response({
                "error": "Video must be downloaded or have a video URL to reprocess"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if video is currently being processed
        if (video.transcription_status == 'transcribing' or 
            video.ai_processing_status == 'processing' or
            video.script_status == 'generating' or
            video.synthesis_status == 'synthesizing'):
            return Response({
                "error": "Video is currently being processed. Please wait for current process to complete."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Reset all processing states
            video.transcription_status = 'not_transcribed'
            video.transcript = ''
            video.transcript_without_timestamps = ''
            video.transcript_hindi = ''
            video.transcript_language = ''
            video.transcript_started_at = None
            video.transcript_processed_at = None
            video.transcript_error_message = ''
            
            video.ai_processing_status = 'not_processed'
            video.ai_summary = ''
            video.ai_tags = ''
            video.ai_processed_at = None
            video.ai_error_message = ''
            
            video.script_status = 'not_generated'
            video.hindi_script = ''
            video.script_error_message = ''
            video.script_generated_at = None
            
            video.synthesis_status = 'not_synthesized'
            video.synthesis_error = ''
            if video.synthesized_audio:
                try:
                    video.synthesized_audio.delete(save=False)
                except Exception:
                    pass
                video.synthesized_audio = None
            
            # Delete processed video files if they exist
            if video.voice_removed_video:
                try:
                    video.voice_removed_video.delete(save=False)
                except Exception:
                    pass
                video.voice_removed_video = None
            video.voice_removed_video_url = ''
            
            if video.final_processed_video:
                try:
                    video.final_processed_video.delete(save=False)
                except Exception:
                    pass
                video.final_processed_video = None
            video.final_processed_video_url = ''
            
            # Reset review status
            video.review_status = 'pending_review'
            video.review_notes = ''
            video.reviewed_at = None
            
            video.save()
            
            # Trigger the full transcription pipeline by calling the transcribe action's logic
            # This will automatically run: transcription -> AI processing -> script generation -> TTS -> video processing
            try:
                # Set status to transcribing
                video.transcription_status = 'transcribing'
                video.transcript_started_at = timezone.now()
                video.save()
                
                # Call transcribe_video which will trigger the full pipeline in the transcribe action
                # We'll run this in a way that triggers the full automated pipeline
                # The transcribe action handles the full pipeline automatically, so we'll just
                # trigger it by calling the same logic
                result = transcribe_video(video)
                
                if result['status'] == 'success':
                    # Save transcript data
                    transcript_text = result.get('text', '')
                    timestamped_text = result.get('transcript_with_timestamps', '')
                    transcript_without_timestamps = result.get('transcript_without_timestamps', transcript_text)
                    srt_text = result.get('srt', '')
                    
                    if timestamped_text:
                        video.transcript = timestamped_text
                    elif srt_text:
                        from .utils import convert_srt_to_timestamped_text
                        video.transcript = convert_srt_to_timestamped_text(srt_text) or srt_text
                    else:
                        video.transcript = transcript_text
                    
                    if transcript_without_timestamps:
                        video.transcript_without_timestamps = transcript_without_timestamps
                    elif timestamped_text:
                        import re
                        plain_text = re.sub(r'^\d{2}:\d{2}:\d{2}\s+', '', timestamped_text, flags=re.MULTILINE)
                        plain_text = '\n'.join([line.strip() for line in plain_text.split('\n') if line.strip()])
                        video.transcript_without_timestamps = plain_text
                    else:
                        video.transcript_without_timestamps = transcript_text
                    
                    hindi_transcript = result.get('text_hindi', '')
                    if not hindi_transcript and transcript_without_timestamps:
                        from .utils import translate_text
                        print(f"Translating transcript to Hindi (language: {result.get('language', 'unknown')})...")
                        hindi_transcript = translate_text(transcript_without_timestamps, target='hi')
                    
                    video.transcript_hindi = hindi_transcript
                    video.transcript_language = result.get('language', '')
                    video.transcription_status = 'transcribed'
                    video.transcript_processed_at = timezone.now()
                    video.transcript_error_message = ''
                    video.save()
                    
                    # Continue with AI processing, script generation, TTS, and video processing
                    # This is the same logic as in the transcribe action
                    try:
                        video.ai_processing_status = 'processing'
                        video.save()
                        
                        ai_result = process_video_with_ai(video)
                        
                        if ai_result['status'] == 'success':
                            video.ai_processing_status = 'processed'
                            video.ai_summary = ai_result.get('summary', '')
                            video.ai_tags = ai_result.get('tags', [])
                            video.ai_processed_at = timezone.now()
                            video.ai_error_message = ''
                            video.save()
                        else:
                            video.ai_processing_status = 'failed'
                            video.ai_error_message = ai_result.get('error', 'Unknown error')
                            video.save()
                    except Exception as e:
                        print(f"AI processing error during reprocess: {e}")
                        video.ai_processing_status = 'failed'
                        video.ai_error_message = str(e)
                        video.save()
                    
                    # Script generation
                    try:
                        video.script_status = 'generating'
                        video.save()
                        
                        script_result = generate_hindi_script(video)
                        
                        if script_result['status'] == 'success':
                            video.hindi_script = script_result['script']
                            video.script_status = 'generated'
                            video.script_generated_at = timezone.now()
                            video.script_error_message = ''
                            video.save()
                        else:
                            video.script_status = 'failed'
                            video.script_error_message = script_result.get('error', 'Unknown error')
                            video.save()
                    except Exception as e:
                        print(f"Script generation error during reprocess: {e}")
                        video.script_status = 'failed'
                        video.script_error_message = str(e)
                        video.save()
                    
                    # Step 4: TTS Generation (automatically after script generation)
                    if video.script_status == 'generated' and video.hindi_script:
                        try:
                            video.synthesis_status = 'synthesizing'
                            video.save()
                            
                            from .utils import get_clean_script_for_tts
                            clean_script = get_clean_script_for_tts(video.hindi_script)
                            
                            # Use XTTS service for TTS generation
                            from .xtts_service import XTTSService, TTS_AVAILABLE
                            if TTS_AVAILABLE:
                                service = XTTSService()
                                
                                import tempfile
                                import os
                                temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
                                temp_audio_path = temp_audio.name
                                temp_audio.close()
                                
                                speaker_wav = None
                                if video.voice_profile and video.voice_profile.reference_audio:
                                    speaker_wav = video.voice_profile.reference_audio.path
                                
                                if not speaker_wav:
                                    print("No voice profile available, skipping TTS generation")
                                    video.synthesis_status = 'failed'
                                    video.synthesis_error = 'No voice profile available for TTS'
                                    video.save()
                                else:
                                    # Generate TTS audio
                                    service.generate_speech(
                                        text=clean_script,
                                        speaker_wav_path=speaker_wav,
                                        language='hi',
                                        output_path=temp_audio_path,
                                        speed=video.tts_speed,
                                        temperature=video.tts_temperature,
                                        repetition_penalty=video.tts_repetition_penalty
                                    )
                                    
                                    # Adjust audio duration to match video duration if available
                                    if video.duration and os.path.exists(temp_audio_path):
                                        from .utils import get_audio_duration, adjust_audio_duration
                                        audio_duration = get_audio_duration(temp_audio_path)
                                        if audio_duration:
                                            duration_diff = abs(audio_duration - video.duration)
                                            if duration_diff > 0.5:
                                                print(f"Adjusting TTS audio duration: {audio_duration:.2f}s -> {video.duration:.2f}s")
                                                adjusted_path = adjust_audio_duration(temp_audio_path, video.duration)
                                                if adjusted_path and adjusted_path != temp_audio_path:
                                                    if os.path.exists(temp_audio_path):
                                                        os.unlink(temp_audio_path)
                                                    temp_audio_path = adjusted_path
                                    
                                    # Save audio file
                                    from django.core.files import File
                                    with open(temp_audio_path, 'rb') as f:
                                        video.synthesized_audio.save(f"synthesized_audio_{video.pk}.wav", File(f), save=False)
                                    
                                    video.synthesis_status = 'synthesized'
                                    video.synthesis_error = ''
                                    video.save()
                                    
                                    # Clean up temp file
                                    if os.path.exists(temp_audio_path):
                                        os.unlink(temp_audio_path)
                                    
                                    print(f"TTS audio generated successfully for video {video.pk}")
                                    
                                    # Step 5: Remove audio from video and combine with new TTS audio
                                    if video.synthesis_status == 'synthesized' and video.synthesized_audio and video.local_file:
                                        from .utils import find_ffmpeg
                                        import subprocess
                                        
                                        ffmpeg_path = find_ffmpeg()
                                        if ffmpeg_path and os.path.exists(video.local_file.path):
                                            try:
                                                # Step 5a: Remove audio
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
                                                    with open(temp_no_audio_path, 'rb') as f:
                                                        video.voice_removed_video.save(f"voice_removed_{video.pk}.mp4", File(f), save=False)
                                                    voice_removed_url = request.build_absolute_uri(video.voice_removed_video.url)
                                                    video.voice_removed_video_url = voice_removed_url
                                                    video.save()
                                                    os.unlink(temp_no_audio_path)
                                                    
                                                    # Step 5b: Combine TTS audio with video
                                                    if os.path.exists(video.synthesized_audio.path):
                                                        voice_removed_file_path = video.voice_removed_video.path
                                                        temp_final = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                                                        temp_final_path = temp_final.name
                                                        temp_final.close()
                                                        
                                                        cmd = [
                                                            ffmpeg_path,
                                                            '-i', voice_removed_file_path,
                                                            '-i', video.synthesized_audio.path,
                                                            '-c:v', 'copy',
                                                            '-c:a', 'aac',
                                                            '-b:a', '192k',
                                                            '-map', '0:v:0',
                                                            '-map', '1:a:0',
                                                            '-shortest',
                                                            '-y',
                                                            temp_final_path
                                                        ]
                                                        
                                                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                                                        if result.returncode == 0 and os.path.exists(temp_final_path):
                                                            with open(temp_final_path, 'rb') as f:
                                                                video.final_processed_video.save(f"final_{video.pk}.mp4", File(f), save=False)
                                                            final_video_url = request.build_absolute_uri(video.final_processed_video.url)
                                                            video.final_processed_video_url = final_video_url
                                                            video.review_status = 'pending_review'
                                                            video.save()
                                                            os.unlink(temp_final_path)
                                                            print(f"✓ Reprocess completed: Final video created")
                                                        else:
                                                            error_msg = f"ffmpeg combine failed: {result.stderr[:500] if result.stderr else 'Unknown error'}"
                                                            print(f"✗ Step 5b (ffmpeg) failed: {error_msg}")
                                                            video.synthesis_error = error_msg
                                                            video.save()
                                                            if os.path.exists(temp_final_path):
                                                                os.unlink(temp_final_path)
                                                    else:
                                                        error_msg = "Synthesized audio file not found"
                                                        print(f"✗ Step 5b (ffmpeg) failed: {error_msg}")
                                                        video.synthesis_error = error_msg
                                                        video.save()
                                                else:
                                                    error_msg = f"ffmpeg remove audio failed: {result.stderr[:500] if result.stderr else 'Unknown error'}"
                                                    print(f"✗ Step 5a (ffmpeg) failed: {error_msg}")
                                                    video.synthesis_error = error_msg
                                                    video.save()
                                                    if os.path.exists(temp_no_audio_path):
                                                        os.unlink(temp_no_audio_path)
                                            except subprocess.TimeoutExpired:
                                                error_msg = "ffmpeg processing timed out (exceeded 5 minutes)"
                                                print(f"✗ {error_msg}")
                                                video.synthesis_error = error_msg
                                                video.save()
                                            except Exception as e:
                                                error_msg = f"ffmpeg processing error: {str(e)}"
                                                print(f"✗ {error_msg}")
                                                import traceback
                                                traceback.print_exc()
                                                video.synthesis_error = error_msg
                                                video.save()
                            else:
                                print("TTS not available, skipping audio generation")
                                video.synthesis_status = 'failed'
                                video.synthesis_error = 'TTS service not available'
                                video.save()
                        except Exception as e:
                            print(f"TTS generation error during reprocess: {e}")
                            import traceback
                            traceback.print_exc()
                            video.synthesis_status = 'failed'
                            video.synthesis_error = str(e)
                            video.save()
                    
                    return Response({
                        "status": "success",
                        "message": "Video reprocessing completed successfully.",
                        "video_id": video.id
                    })
                else:
                    video.transcription_status = 'failed'
                    video.transcript_error_message = result.get('error', 'Unknown error')
                    video.save()
                    return Response({
                        "status": "failed",
                        "error": result.get('error', 'Unknown error'),
                        "step": "transcription"
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    
            except Exception as e:
                print(f"Error during reprocess: {e}")
                import traceback
                traceback.print_exc()
                video.transcription_status = 'failed'
                video.transcript_error_message = str(e)
                video.save()
                return Response({
                    "status": "failed",
                    "error": f"Error starting reprocess: {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            print(f"Error during reprocess: {e}")
            import traceback
            traceback.print_exc()
            return Response({
                "status": "failed",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['delete', 'post'])
    def delete(self, request, pk=None):
        """Delete a video"""
        video = self.get_object()
        
        try:
            # Delete associated files if they exist
            if video.local_file:
                try:
                    video.local_file.delete(save=False)
                except Exception:
                    pass  # File might not exist
            
            if video.synthesized_audio:
                try:
                    video.synthesized_audio.delete(save=False)
                except Exception:
                    pass
            
            # Delete the video record
            video.delete()
            
            return Response({
                "status": "success",
                "message": "Video deleted successfully"
            })
        except Exception as e:
            return Response({
                "status": "failed",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class AISettingsViewSet(viewsets.ViewSet):
    """ViewSet for AI Provider Settings"""

    def list(self, request):
        """Get current AI settings"""
        settings = AIProviderSettings.objects.first()
        if not settings:
            return Response({"provider": "gemini", "api_key": ""})

        serializer = AIProviderSettingsSerializer(settings)
        return Response(serializer.data)

    def create(self, request):
        """Update AI settings"""
        provider = request.data.get('provider', 'gemini')
        api_key = request.data.get('api_key', '')

        settings, created = AIProviderSettings.objects.get_or_create(
            id=1,
            defaults={"provider": provider, "api_key": api_key}
        )

        if not created:
            settings.provider = provider
            settings.api_key = api_key
            settings.save()

        return Response({"status": "saved", "provider": provider})




@api_view(['GET'])
def dashboard_stats(request):
    """Get dashboard statistics"""
    stats = {
        'total_videos': VideoDownload.objects.count(),
        'successful_extractions': VideoDownload.objects.filter(status='success').count(),
        'downloaded_locally': VideoDownload.objects.filter(is_downloaded=True).count(),
        'transcribed': VideoDownload.objects.filter(transcription_status='transcribed').count(),
        'ai_processed': VideoDownload.objects.filter(ai_processing_status='processed').count(),
        'audio_prompts_generated': 0,  # Field removed from model, keeping for frontend compatibility
        'synthesized': VideoDownload.objects.filter(synthesis_status='synthesized').count(),
        'failed': VideoDownload.objects.filter(status='failed').count(),
    }

    serializer = DashboardStatsSerializer(stats)
    return Response(serializer.data)


@api_view(['POST'])
def bulk_download(request):
    """Bulk download videos"""
    serializer = BulkActionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    video_ids = serializer.validated_data['video_ids']
    videos = VideoDownload.objects.filter(id__in=video_ids)

    results = []
    for video in videos:
        if video.is_downloaded and video.local_file:
            results.append({
                "id": video.id,
                "status": "already_downloaded"
            })
            continue

        if not video.video_url:
            results.append({
                "id": video.id,
                "status": "failed",
                "error": "No video URL available"
            })
            continue

        try:
            file_content = download_file(video.video_url)
            if file_content:
                filename = f"{video.video_id or video.id}.mp4"
                video.local_file.save(filename, file_content)
                video.is_downloaded = True
                video.save()
                results.append({
                    "id": video.id,
                    "status": "success"
                })
            else:
                results.append({
                    "id": video.id,
                    "status": "failed",
                    "error": "Download failed"
                })
        except Exception as e:
            results.append({
                "id": video.id,
                "status": "failed",
                "error": str(e)
            })

    return Response({"results": results})


@api_view(['POST'])
def bulk_transcribe(request):
    """Bulk transcribe videos"""
    serializer = BulkActionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    video_ids = serializer.validated_data['video_ids']
    videos = VideoDownload.objects.filter(id__in=video_ids)

    results = []
    for video in videos:
        if video.transcription_status in ['transcribing', 'transcribed']:
            results.append({
                "id": video.id,
                "status": video.transcription_status
            })
            continue

        video.transcription_status = 'transcribing'
        video.transcript_started_at = timezone.now()
        video.save()

        try:
            result = transcribe_video(video)

            if result['status'] == 'success':
                video.transcription_status = 'transcribed'
                video.transcript = result.get('text', '')
                video.transcript_hindi = result.get('text_hindi', '')
                video.transcript_language = result.get('language', '')
                video.transcript_processed_at = timezone.now()
                video.save()
                results.append({
                    "id": video.id,
                    "status": "success"
                })
            else:
                video.transcription_status = 'failed'
                video.transcript_error_message = result.get('error', '')
                video.save()
                results.append({
                    "id": video.id,
                    "status": "failed",
                    "error": result.get('error', '')
                })
        except Exception as e:
            video.transcription_status = 'failed'
            video.transcript_error_message = str(e)
            video.save()
            results.append({
                "id": video.id,
                "status": "failed",
                "error": str(e)
            })

    return Response({"results": results})


@api_view(['POST'])
def bulk_process_ai(request):
    """Bulk AI processing"""
    serializer = BulkActionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    video_ids = serializer.validated_data['video_ids']
    videos = VideoDownload.objects.filter(id__in=video_ids)

    results = []
    for video in videos:
        if video.ai_processing_status in ['processing', 'processed']:
            results.append({
                "id": video.id,
                "status": video.ai_processing_status
            })
            continue

        video.ai_processing_status = 'processing'
        video.save()

        try:
            result = process_video_with_ai(video)

            if result['status'] == 'success':
                video.ai_processing_status = 'processed'
                video.ai_summary = result.get('summary', '')
                video.ai_tags = result.get('tags', '')
                video.ai_processed_at = timezone.now()
                video.save()
                results.append({
                    "id": video.id,
                    "status": "success"
                })
            else:
                video.ai_processing_status = 'failed'
                video.ai_error_message = result.get('error', '')
                video.save()
                results.append({
                    "id": video.id,
                    "status": "failed",
                    "error": result.get('error', '')
                })
        except Exception as e:
            video.ai_processing_status = 'failed'
            video.ai_error_message = str(e)
            video.save()
            results.append({
                "id": video.id,
                "status": "failed",
                "error": str(e)
            })

    return Response({"results": results})


@api_view(['POST'])
def bulk_delete(request):
    """Bulk delete videos"""
    serializer = BulkActionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    video_ids = serializer.validated_data['video_ids']
    videos = VideoDownload.objects.filter(id__in=video_ids)
    
    deleted_count = 0
    results = []
    
    for video in videos:
        try:
            # Delete associated files if they exist
            if video.local_file:
                try:
                    video.local_file.delete(save=False)
                except Exception:
                    pass  # File might not exist
            
            if video.synthesized_audio:
                try:
                    video.synthesized_audio.delete(save=False)
                except Exception:
                    pass
            
            # Delete the video record
            video.delete()
            deleted_count += 1
            results.append({
                "id": video.id,
                "status": "deleted"
            })
        except Exception as e:
            results.append({
                "id": video.id,
                "status": "failed",
                "error": str(e)
            })

    return Response({
        "deleted_count": deleted_count,
        "results": results
    })

