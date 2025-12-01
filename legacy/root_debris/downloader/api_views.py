"""
REST API Views for RedNote Downloader
"""
import os
import logging
from django.utils import timezone
from django.db.models import Count, Q
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny

logger = logging.getLogger(__name__)

from .models import VideoDownload, AIProviderSettings, CloudinarySettings, GoogleSheetsSettings, WatermarkSettings
from .serializers import (
    VideoDownloadSerializer, VideoDownloadListSerializer,
    AIProviderSettingsSerializer, VideoExtractSerializer,
    VideoTranscribeSerializer, BulkActionSerializer, DashboardStatsSerializer,
    CloudinarySettingsSerializer, GoogleSheetsSettingsSerializer, WatermarkSettingsSerializer
)
from .utils import (
    perform_extraction, extract_video_id, detect_video_source, translate_text,
    transcribe_video, download_file,
    process_video_with_ai, get_video_duration,
    calculate_tts_parameters, generate_hindi_script, generate_video_metadata
)
# Optional imports - these services may not be installed
try:
    from .cloudinary_service import upload_video_file
except ImportError:
    upload_video_file = None
    logger.warning("Cloudinary service not available (cloudinary package not installed)")

try:
    from .google_sheets_service import add_video_to_sheet
except ImportError:
    add_video_to_sheet = None
    logger.warning("Google Sheets service not available (google packages not installed)")


def calculate_optimal_tts_speed(video):
    """
    Calculate optimal TTS speed to match video duration
    
    Args:
        video: VideoDownload instance
    
    Returns:
        float: TTS speed multiplier (e.g., 1.2 means 20% faster)
    """
    if not video.duration or not video.hindi_script:
        return 1.0  # Default speed
    
    # Estimate script reading time at normal speed
    # Average Hindi reading speed: ~150 words/minute = 2.5 words/second
    from .utils import get_clean_script_for_tts
    clean_script = get_clean_script_for_tts(video.hindi_script)
    word_count = len(clean_script.split())
    
    # Estimated duration at normal speed (in seconds)
    estimated_duration = word_count / 2.5
    
    # Calculate speed adjustment
    target_duration = video.duration * 0.95  # Leave 5% buffer
    
    if estimated_duration <= target_duration:
        return 1.0  # No speed adjustment needed
    
    # Calculate required speed
    required_speed = estimated_duration / target_duration
    
    # Clamp between 0.8x (slower) and 1.5x (faster)
    # Don't go too fast or it sounds unnatural
    optimal_speed = max(0.8, min(1.5, required_speed))
    
    print(f"📊 Speed Calculation:")
    print(f"   Video duration: {video.duration}s")
    print(f"   Word count: {word_count}")
    print(f"   Estimated speech: {estimated_duration:.1f}s")
    print(f"   Optimal speed: {optimal_speed:.2f}x")
    
    return optimal_speed



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

        # Check if transcription is stuck (running for more than 30 minutes)
        if video.transcription_status == 'transcribing' and video.transcript_started_at:
            elapsed_minutes = (timezone.now() - video.transcript_started_at).total_seconds() / 60
            if elapsed_minutes > 30:
                # Reset stuck transcription
                print(f"⚠️  Transcription stuck for {elapsed_minutes:.1f} minutes, resetting...")
                video.transcription_status = 'not_transcribed'
                video.transcript_started_at = None
                video.transcript_error_message = f"Previous transcription timed out after {elapsed_minutes:.1f} minutes"
                video.save()
            else:
                return Response({
                    "status": "already_processing",
                    "message": "Processing is already in progress",
                    "current_step": "transcribing",
                    "elapsed_minutes": int(elapsed_minutes)
                })

        if not video.is_downloaded and not video.video_url:
            return Response({
                "error": "Video must be downloaded or have a video URL to transcribe"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Step 1: Transcription
        video.transcription_status = 'transcribing'
        video.transcript_started_at = timezone.now()
        video.save()
        
        print(f"🔄 Starting transcription for video {video.id} (title: {video.title[:50]}...)")
        transcription_start_time = timezone.now()
        
        # Initialize variables to avoid "referenced before assignment" errors
        transcript_text = ''
        timestamped_text = ''
        transcript_without_timestamps = ''
        srt_text = ''

        try:
            # Transcribe video with timeout protection
            # Use threading to add timeout for transcription (max 15 minutes)
            import threading
            import queue
            
            transcription_timeout = 15 * 60  # 15 minutes max
            result_queue = queue.Queue()
            exception_queue = queue.Queue()
            
            def run_transcription():
                try:
                    result = transcribe_video(video)
                    result_queue.put(result)
                except Exception as e:
                    exception_queue.put(e)
            
            transcription_thread = threading.Thread(target=run_transcription, daemon=True)
            transcription_thread.start()
            transcription_thread.join(timeout=transcription_timeout)
            
            if transcription_thread.is_alive():
                # Transcription is taking too long - timeout
                error_msg = f"Transcription timed out after {transcription_timeout // 60} minutes. The video may be too long or the transcription service is unresponsive."
                print(f"⚠️  {error_msg}")
                video.transcription_status = 'failed'
                video.transcript_error_message = error_msg
                video.save()
                
                return Response({
                    "status": "failed",
                    "error": error_msg,
                    "step": "transcription"
                }, status=status.HTTP_408_REQUEST_TIMEOUT)
            
            # Get result from queue
            if not exception_queue.empty():
                raise exception_queue.get()
            
            if result_queue.empty():
                error_msg = "Transcription completed but returned no result. This may indicate an internal error."
                print(f"⚠️  {error_msg}")
                video.transcription_status = 'failed'
                video.transcript_error_message = error_msg
                video.save()
                
                return Response({
                    "status": "failed",
                    "error": error_msg,
                    "step": "transcription"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            result = result_queue.get()
            
            transcription_duration = (timezone.now() - transcription_start_time).total_seconds()
            print(f"✓ Transcription completed in {transcription_duration:.1f} seconds")

            # Handle dual transcription results (returns different structure)
            # Initialize variables to avoid "referenced before assignment" errors
            transcript_text = ''
            timestamped_text = ''
            transcript_without_timestamps = ''
            srt_text = ''
            
            if result.get('status') in ['success', 'partial']:
                # Dual transcription mode - extract the best result
                if 'whisper_result' in result or 'nca_result' in result:
                    # Use Whisper result if available (more reliable), otherwise NCA
                    # Refresh video to get latest data saved by dual transcription
                    video.refresh_from_db()
                    
                    if result.get('whisper_result') and result['whisper_result'].get('status') == 'success':
                        whisper_result = result['whisper_result']
                        # Convert to standard format using data already saved to video
                        result = {
                            'status': 'success',
                            'text': video.whisper_transcript_without_timestamps or whisper_result.get('text', ''),
                            'transcript_with_timestamps': video.whisper_transcript or '',
                            'transcript_without_timestamps': video.whisper_transcript_without_timestamps or whisper_result.get('text', ''),
                            'text_hindi': video.whisper_transcript_hindi or '',
                            'language': video.whisper_transcript_language or whisper_result.get('language', ''),
                            'srt': '',  # Can be generated from segments if needed
                            'segments': whisper_result.get('segments', [])
                        }
                        # Also update main transcript fields from Whisper (dual transcription saves to whisper_* fields)
                        if not video.transcript or video.transcription_status != 'transcribed':
                            video.transcription_status = 'transcribed'
                            video.transcript = video.whisper_transcript
                            video.transcript_without_timestamps = video.whisper_transcript_without_timestamps
                            video.transcript_hindi = video.whisper_transcript_hindi
                            video.transcript_language = video.whisper_transcript_language
                            video.transcript_processed_at = timezone.now()
                            video.save()
                        print(f"✓ Using Whisper result from dual transcription: {len(result.get('text', ''))} chars")
                    elif result.get('nca_result') and result['nca_result'].get('status') == 'success':
                        nca_result = result['nca_result']
                        # Convert to standard format using data already saved to video
                        result = {
                            'status': 'success',
                            'text': video.transcript_without_timestamps or nca_result.get('text', ''),
                            'transcript_with_timestamps': video.transcript or '',
                            'transcript_without_timestamps': video.transcript_without_timestamps or nca_result.get('text', ''),
                            'text_hindi': video.transcript_hindi or '',
                            'language': video.transcript_language or nca_result.get('language', ''),
                            'srt': nca_result.get('srt', ''),
                            'segments': nca_result.get('segments', [])
                        }
                        print(f"✓ Using NCA result from dual transcription: {len(result.get('text', ''))} chars")
                    else:
                        # Both failed, but we have partial result - use whatever is available
                        error_msg = "Both NCA and Whisper transcription failed in dual mode"
                        if result.get('whisper_result'):
                            error_msg = result['whisper_result'].get('error', error_msg)
                        elif result.get('nca_result'):
                            error_msg = result['nca_result'].get('error', error_msg)
                        result = {
                            'status': 'failed',
                            'error': error_msg
                        }

            if result.get('status') == 'success':
                # Refresh video to get latest data (dual transcription may have already saved it)
                video.refresh_from_db()
                
                # Only update if not already set (dual transcription may have already saved to video)
                if not video.transcript or video.transcription_status != 'transcribed':
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
                    # If transcript is in Arabic/Urdu, translate it to Hindi using AI for better quality
                    hindi_transcript = result.get('text_hindi', '')
                    if not hindi_transcript and transcript_without_timestamps:
                        # If Hindi translation not provided, translate the plain text using AI
                        from .utils import translate_text_with_ai
                        print(f"Translating transcript to Hindi using AI (preserves meaning) (language: {result.get('language', 'unknown')})...")
                        hindi_transcript = translate_text_with_ai(transcript_without_timestamps, target='hi')
                    
                    video.transcript_hindi = hindi_transcript
                    video.transcript_language = result.get('language', '')
                    video.transcript_processed_at = timezone.now()
                    video.transcript_error_message = ''
                    video.save()
                else:
                    print(f"✓ Transcript already saved by dual transcription, using existing data")

                # Step 2: AI Processing (automatically after transcription)
                # NOTE: AI enhancement (enhance_transcript_with_ai) already happens during transcription
                # and sets ai_processing_status. Here we only do summary/tags generation if needed.
                try:
                    # Refresh from DB to get latest state (AI enhancement may have already set status)
                    video.refresh_from_db()
                    
                    # Only run process_video_with_ai if AI enhancement is already done
                    # (process_video_with_ai generates summary/tags, not the enhanced transcript)
                    if video.ai_processing_status == 'processed':
                        # AI enhancement already completed, just generate summary/tags
                        print(f"AI enhancement already completed, generating summary/tags...")
                        ai_result = process_video_with_ai(video)
                        
                        if ai_result['status'] == 'success':
                            video.ai_summary = ai_result.get('summary', '')
                            video.ai_tags = ai_result.get('tags', [])
                            video.ai_processed_at = timezone.now()
                            video.ai_error_message = ''
                            video.save()
                        else:
                            # Keep status as 'processed' but log the error
                            video.ai_error_message = ai_result.get('error', 'Unknown error')
                            video.save()
                    elif video.ai_processing_status == 'processing':
                        # AI enhancement is still in progress (shouldn't happen here, but handle it)
                        print(f"AI enhancement still in progress, waiting...")
                    elif video.ai_processing_status == 'failed':
                        # AI enhancement failed, don't try to generate summary
                        print(f"AI enhancement failed, skipping summary generation")
                    else:
                        # AI enhancement not started yet (shouldn't happen, but handle it)
                        print(f"AI enhancement not started, setting status to processing...")
                        video.ai_processing_status = 'processing'
                        video.save(update_fields=['ai_processing_status'])
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
                    import traceback
                    traceback.print_exc()
                    # Only update status if it's not already set by AI enhancement
                    video.refresh_from_db()
                    if video.ai_processing_status not in ['processed', 'failed']:
                        video.ai_processing_status = 'failed'
                        video.ai_error_message = str(e)
                        video.save(update_fields=['ai_processing_status', 'ai_error_message'])

                # Step 3: Script Generation (automatically after AI processing)
                # Generate script if we have transcript (NCA/Whisper) and enhanced transcript
                # Visual Analysis is OPTIONAL - if available, it will be included; if not, continue without it
                has_transcript = video.transcript or video.whisper_transcript
                has_enhanced = video.enhanced_transcript
                has_visual = video.visual_transcript  # Optional
                
                if not has_transcript:
                    print("⚠ Script generation skipped: No transcript available (NCA/Whisper)")
                    video.script_status = 'failed'
                    video.script_error_message = 'No transcript available. Please ensure transcription completes successfully.'
                    video.save()
                elif not has_enhanced:
                    print("⚠ Script generation skipped: Enhanced transcript not available")
                    video.script_status = 'failed'
                    video.script_error_message = 'Enhanced transcript is required for script generation. Please wait for AI enhancement to complete.'
                    video.save()
                else:
                    try:
                        video.script_status = 'generating'
                        video.save()
                        print(f"✓ Starting Hindi script generation (explainer style)...")
                        print(f"  - Transcript (NCA/Whisper): ✓")
                        print(f"  - Enhanced Transcript: ✓")
                        print(f"  - Visual Analysis: {'✓ (available)' if has_visual else '⚠ (optional - not available, continuing without it)'}")
                        
                        # Generate script with timeout protection
                        import threading
                        import queue
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
                            # Script generation timed out
                            error_msg = "Script generation timed out after 5 minutes"
                            print(f"✗ {error_msg}")
                            video.script_status = 'failed'
                            video.script_error_message = error_msg
                            video.save()
                        elif not exception_queue.empty():
                            # Exception occurred
                            e = exception_queue.get()
                            error_msg = f"Script generation error: {str(e)}"
                            print(f"✗ {error_msg}")
                            import traceback
                            traceback.print_exc()
                            video.script_status = 'failed'
                            video.script_error_message = error_msg
                            video.save()
                        elif not script_queue.empty():
                            # Script generation completed
                            script_result = script_queue.get()
                            
                            if script_result['status'] == 'success':
                                video.hindi_script = script_result['script']
                                video.script_status = 'generated'
                                video.script_generated_at = timezone.now()
                                video.script_error_message = ''
                                video.save()
                                print(f"✓ Hindi script generated successfully (explainer style)")
                            else:
                                video.script_status = 'failed'
                                video.script_error_message = script_result.get('error', 'Unknown error')
                                video.save()
                                print(f"✗ Script generation failed: {script_result.get('error', 'Unknown error')}")
                        else:
                            # No result and no exception - something went wrong
                            error_msg = "Script generation completed but no result was returned"
                            print(f"✗ {error_msg}")
                            video.script_status = 'failed'
                            video.script_error_message = error_msg
                            video.save()
                    except Exception as e:
                        print(f"Script generation error: {e}")
                        import traceback
                        traceback.print_exc()
                        video.script_status = 'failed'
                        video.script_error_message = str(e)
                        video.save()

                # Step 4: TTS Generation (automatically after script generation)
                # Fix: If script exists but status is still 'generating', update status to 'generated'
                if video.hindi_script and video.script_status == 'generating':
                    print(f"⚠ Script exists but status is 'generating' - fixing status to 'generated'")
                    video.script_status = 'generated'
                    if not video.script_generated_at:
                        video.script_generated_at = timezone.now()
                    video.save()
                
                tts_audio_url = None
                if video.script_status == 'generated' and video.hindi_script:
                    try:
                        video.synthesis_status = 'synthesizing'
                        video.save()
                        
                        from .utils import get_clean_script_for_tts
                        clean_script = get_clean_script_for_tts(video.hindi_script)
                        
                        # Use Gemini TTS service for TTS generation
                        from .gemini_tts_service import GeminiTTSService, GEMINI_TTS_AVAILABLE
                        import tempfile
                        import os
                        
                        if not GEMINI_TTS_AVAILABLE:
                            logger.error("Gemini TTS not available")
                            video.synthesis_status = 'failed'
                            video.synthesis_error = 'Gemini TTS service not available'
                            video.save()
                        else:
                            try:
                                # Get Gemini API key from AIProviderSettings
                                from .models import AIProviderSettings
                                settings_obj = AIProviderSettings.objects.first()
                                api_key = settings_obj.get_api_key('gemini') if settings_obj else None
                                
                                if not api_key:
                                    raise Exception("Gemini API key not configured. Please set it in AI Provider Settings.")
                                
                                service = GeminiTTSService(api_key=api_key)
                                
                                # Create temp audio file (Gemini TTS generates MP3)
                                temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                                temp_audio_path = temp_audio.name
                                temp_audio.close()
                                
                                # Get TTS settings from video model
                                tts_temperature = video.tts_temperature if video.tts_temperature else 0.75
                                
                                # Use Enceladus voice for Hindi (as specified in n8n workflow)
                                voice_name = 'Enceladus'
                                language_code = 'hi-IN'  # Hindi (India)
                                
                                # Let GeminiTTSService generate comprehensive style prompt automatically
                                # It will analyze content and create optimal prompt with all best practices
                                style_prompt = None  # Let service generate comprehensive prompt
                                
                                # Generate TTS audio using Gemini TTS
                                print(f"Generating TTS with Gemini TTS (voice: {voice_name}, language: {language_code}, temp: {tts_temperature})...")
                                tts_success = False
                                try:
                                    service.generate_speech(
                                        text=clean_script,
                                        language_code=language_code,
                                        voice_name=voice_name,
                                        output_path=temp_audio_path,
                                        temperature=tts_temperature,
                                        style_prompt=style_prompt,
                                        video_duration=video.duration  # Pass video duration for timeout calculation
                                    )
                                    tts_success = True
                                except Exception as e:
                                    error_msg = f"TTS generation failed: {str(e)}"
                                    logger.error(error_msg, exc_info=True)
                                    video.synthesis_status = 'failed'
                                    video.synthesis_error = error_msg
                                    video.save()
                                    # Don't re-raise - continue with pipeline even if TTS fails
                                    # The response will indicate partial success with a warning
                                    print(f"✗ {error_msg}")
                                
                                # Only proceed with saving audio if TTS succeeded
                                if tts_success and os.path.exists(temp_audio_path):
                                    # Check audio duration and adjust if needed
                                    if video.duration:
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
                                                print(f"✓ TTS audio duration ({audio_duration:.2f}s) matches video duration ({video.duration:.2f}s)")
                                    
                                    # Save audio file (Gemini TTS generates MP3)
                                    from django.core.files import File
                                    with open(temp_audio_path, 'rb') as f:
                                        video.synthesized_audio.save(f"synthesized_audio_{video.pk}.mp3", File(f), save=False)
                                    
                                    video.synthesis_status = 'synthesized'
                                    video.synthesis_error = ''
                                    video.synthesized_at = timezone.now()
                                    video.save()
                                    
                                    # Clean up temp file
                                    if os.path.exists(temp_audio_path):
                                        os.unlink(temp_audio_path)
                                    
                                    print(f"✓ Gemini TTS audio generated successfully for video {video.pk} (voice: {voice_name})")
                                elif not tts_success:
                                    # TTS failed, but we already set the error status above
                                    print(f"⚠ TTS generation failed, continuing pipeline without audio")
                            except Exception as tts_error:
                                error_msg = f"TTS generation failed: {str(tts_error)}"
                                logger.error(error_msg, exc_info=True)
                                video.synthesis_status = 'failed'
                                video.synthesis_error = error_msg
                                video.save()
                                print(f"✗ {error_msg}")
                                # Don't re-raise - continue with pipeline even if TTS fails
                                # The response will indicate partial success
                    except Exception as e:
                        print(f"TTS generation error: {e}")
                        import traceback
                        traceback.print_exc()
                        video.synthesis_status = 'failed'
                        video.synthesis_error = str(e)
                        video.save()
                        # Don't re-raise - continue with pipeline even if TTS fails

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
                                    
                                    print(f"Running ffmpeg command: {' '.join(cmd)}")
                                    try:
                                        ffmpeg_result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                                    except subprocess.TimeoutExpired:
                                        error_msg = "ffmpeg remove audio timed out after 5 minutes"
                                        print(f"✗ {error_msg}")
                                        video.synthesis_error = error_msg
                                        video.save()
                                        if os.path.exists(temp_no_audio_path):
                                            os.unlink(temp_no_audio_path)
                                        raise
                                    except Exception as e:
                                        error_msg = f"ffmpeg remove audio error: {str(e)}"
                                        print(f"✗ {error_msg}")
                                        video.synthesis_error = error_msg
                                        video.save()
                                        if os.path.exists(temp_no_audio_path):
                                            os.unlink(temp_no_audio_path)
                                        raise
                                    
                                    if ffmpeg_result.returncode == 0 and os.path.exists(temp_no_audio_path):
                                        # Save voice-removed video
                                        from django.core.files import File
                                        with open(temp_no_audio_path, 'rb') as f:
                                            video.voice_removed_video.save(f"voice_removed_{video.pk}.mp4", File(f), save=False)
                                        voice_removed_url = request.build_absolute_uri(video.voice_removed_video.url)
                                        video.voice_removed_video_url = voice_removed_url
                                        video.save()
                                        print(f"✓ Step 5a (ffmpeg) completed: Voice removed video saved")
                                        
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
                                            
                                            print(f"Running ffmpeg combine command: {' '.join(cmd)}")
                                            try:
                                                ffmpeg_result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                                            except subprocess.TimeoutExpired:
                                                error_msg = "ffmpeg combine timed out after 5 minutes"
                                                print(f"✗ {error_msg}")
                                                video.synthesis_error = error_msg
                                                video.save()
                                                if os.path.exists(temp_final_path):
                                                    os.unlink(temp_final_path)
                                                raise
                                            except Exception as e:
                                                error_msg = f"ffmpeg combine error: {str(e)}"
                                                print(f"✗ {error_msg}")
                                                video.synthesis_error = error_msg
                                                video.save()
                                                if os.path.exists(temp_final_path):
                                                    os.unlink(temp_final_path)
                                                raise
                                            
                                            if ffmpeg_result.returncode == 0 and os.path.exists(temp_final_path):
                                                # Step 5c: Apply watermark if enabled
                                                watermark_applied = False
                                                try:
                                                    from .models import WatermarkSettings
                                                    from .watermark_service import apply_moving_watermark
                                                    
                                                    watermark_settings = WatermarkSettings.objects.first()
                                                    if watermark_settings and watermark_settings.enabled and watermark_settings.watermark_text:
                                                        # Create temp file for watermarked video
                                                        temp_watermarked = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                                                        temp_watermarked_path = temp_watermarked.name
                                                        temp_watermarked.close()
                                                        
                                                        # Apply moving text watermark
                                                        if apply_moving_watermark(
                                                            video_path=temp_final_path,
                                                            watermark_text=watermark_settings.watermark_text,
                                                            output_path=temp_watermarked_path,
                                                            position_change_interval=watermark_settings.position_change_interval,
                                                            opacity=watermark_settings.opacity,
                                                            font_size=watermark_settings.font_size,
                                                            font_color=watermark_settings.font_color
                                                        ):
                                                            # Replace temp_final_path with watermarked version
                                                            os.unlink(temp_final_path)
                                                            temp_final_path = temp_watermarked_path
                                                            watermark_applied = True
                                                            print(f"✓ Step 5c (watermark) completed: Moving text watermark applied: '{watermark_settings.watermark_text}'")
                                                        else:
                                                            # Watermark failed, use original
                                                            if os.path.exists(temp_watermarked_path):
                                                                os.unlink(temp_watermarked_path)
                                                            print(f"⚠ Watermark application failed, using video without watermark")
                                                except Exception as e:
                                                    print(f"⚠ Watermark application error: {e}")
                                                    import traceback
                                                    traceback.print_exc()
                                                
                                                # Save final video (with or without watermark)
                                                with open(temp_final_path, 'rb') as f:
                                                    video.final_processed_video.save(f"final_{video.pk}.mp4", File(f), save=False)
                                                final_video_url = request.build_absolute_uri(video.final_processed_video.url)
                                                video.final_processed_video_url = final_video_url
                                                # Set review status to pending_review
                                                video.review_status = 'pending_review'
                                                video.save()
                                                os.unlink(temp_final_path)
                                                print(f"✓ Step 5b (ffmpeg) completed: Final video with new audio created: {final_video_url}")
                                                if watermark_applied:
                                                    print(f"✓ Step 5c (watermark) completed: Video includes moving watermark")
                                                print(f"✓ Video set to 'pending_review' status - ready for review")
                                                
                                                # Generate metadata, upload to Cloudinary, and sync to Google Sheets
                                                # Run post-processing in background to avoid blocking response
                                                import threading
                                                video_id_for_post = video.id
                                                
                                                def post_process_video():
                                                    try:
                                                        # Re-fetch video object in the thread
                                                        from .models import VideoDownload
                                                        video_obj = VideoDownload.objects.get(pk=video_id_for_post)
                                                        
                                                        # Generate metadata using AI
                                                        metadata_result = generate_video_metadata(video_obj)
                                                        if metadata_result.get('status') == 'success':
                                                            video_obj.generated_title = metadata_result.get('title', '')
                                                            video_obj.generated_description = metadata_result.get('description', '')
                                                            video_obj.generated_tags = metadata_result.get('tags', '')
                                                            video_obj.save(update_fields=['generated_title', 'generated_description', 'generated_tags'])
                                                            print(f"✓ Generated metadata: {video_obj.generated_title[:50]}...")
                                                        else:
                                                            print(f"⚠ Metadata generation failed: {metadata_result.get('error', 'Unknown error')}")
                                                        
                                                        # Upload to Cloudinary if enabled (replace existing if same video_id)
                                                        if upload_video_file:
                                                            try:
                                                                # Use video_id as public_id to replace existing video
                                                                video_id_for_cloudinary = video_obj.video_id or str(video_obj.id)
                                                                cloudinary_result = upload_video_file(
                                                                    video_obj.final_processed_video,
                                                                    video_id=video_id_for_cloudinary
                                                                )
                                                                if cloudinary_result:
                                                                    video_obj.cloudinary_url = cloudinary_result.get('secure_url') or cloudinary_result.get('url', '')
                                                                    video_obj.cloudinary_uploaded_at = timezone.now()
                                                                    video_obj.save(update_fields=['cloudinary_url', 'cloudinary_uploaded_at'])
                                                                    print(f"✓ Uploaded to Cloudinary (replaced if exists): {video_obj.cloudinary_url[:50]}...")
                                                            except Exception as e:
                                                                print(f"⚠ Cloudinary upload error: {str(e)}")
                                                        else:
                                                            print("⚠ Cloudinary upload skipped or failed (cloudinary package not installed)")
                                                        
                                                        # Add/Update to Google Sheets if enabled (updates existing if video_id matches)
                                                        # Skip Google Sheets sync in background thread to avoid blocking
                                                        # It will be synced later via manual action or scheduled task
                                                        print("⚠ Google Sheets sync skipped in background (will sync manually later)")
                                                        # if add_video_to_sheet:
                                                        #     try:
                                                        #         sheet_result = add_video_to_sheet(video_obj, video_obj.cloudinary_url)
                                                        #         if sheet_result and sheet_result.get('success'):
                                                        #             print(f"✓ Added/Updated to Google Sheets")
                                                        #         else:
                                                        #             error_msg = sheet_result.get('error', 'Unknown error') if sheet_result else 'Google Sheets not configured'
                                                        #             print(f"⚠ Google Sheets sync failed: {error_msg}")
                                                        #     except Exception as e:
                                                        #         print(f"⚠ Google Sheets sync error: {str(e)}")
                                                        #         import traceback
                                                        #         traceback.print_exc()
                                                        # else:
                                                        #     print("⚠ Google Sheets skipped (google packages not installed)")
                                                    except Exception as e:
                                                        print(f"⚠ Error in post-processing: {str(e)}")
                                                        import traceback
                                                        traceback.print_exc()
                                                
                                                # Start post-processing in background thread (non-blocking)
                                                post_thread = threading.Thread(target=post_process_video, daemon=True)
                                                post_thread.start()
                                                print(f"→ Post-processing (metadata/Cloudinary/Sheets) started in background")
                                            else:
                                                error_msg = f"ffmpeg combine failed: {ffmpeg_result.stderr[:500] if ffmpeg_result.stderr else 'Unknown error'}"
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
                                        error_msg = f"ffmpeg remove audio failed: {ffmpeg_result.stderr[:500] if ffmpeg_result.stderr else 'Unknown error'}"
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
                # Ensure timestamped_text is defined (use from result or video)
                # IMPORTANT: Check if result is a dict before calling .get() (avoid CompletedProcess collision)
                if not timestamped_text:
                    if isinstance(result, dict):
                        timestamped_text = result.get('transcript_with_timestamps', '') or video.transcript or ''
                    else:
                        timestamped_text = video.transcript or ''
                if not transcript_text:
                    if isinstance(result, dict):
                        transcript_text = result.get('text', '') or video.transcript_without_timestamps or ''
                    else:
                        transcript_text = video.transcript_without_timestamps or ''
                if not transcript_without_timestamps:
                    if isinstance(result, dict):
                        transcript_without_timestamps = result.get('transcript_without_timestamps', '') or video.transcript_without_timestamps or transcript_text
                    else:
                        transcript_without_timestamps = video.transcript_without_timestamps or transcript_text
                
                serializer_data.update({
                    "status": "success",
                    "transcript_with_timestamps": timestamped_text,
                    "transcript_without_timestamps": transcript_without_timestamps,
                })
                
                # Check for visual and enhanced errors from dual transcription
                # IMPORTANT: Check if result is a dict before calling .get() (avoid AttributeError)
                visual_error = None
                enhanced_error = None
                if isinstance(result, dict):
                    visual_error = result.get('visual_error')
                    enhanced_error = result.get('enhanced_error')
                
                # Add warnings if visual or enhanced failed
                warnings = []
                if visual_error:
                    warnings.append(f"Visual Analysis: {visual_error}")
                if enhanced_error:
                    warnings.append(f"AI Enhancement: {enhanced_error}")
                
                # Add warning if TTS failed
                if video.synthesis_status == 'failed':
                    warnings.append(f"TTS Generation: {video.synthesis_error or 'Failed'}")
                
                if warnings:
                    serializer_data["warnings"] = warnings
                    logger.warning(f"Transcription completed with warnings for video {video.id}: {warnings}")
                
                # Ensure video URLs are included (serializer should handle this, but add explicit checks)
                if not serializer_data.get('voice_removed_video_url') and voice_removed_url:
                    serializer_data['voice_removed_video_url'] = voice_removed_url
                
                if not serializer_data.get('final_processed_video_url') and final_video_url:
                    serializer_data['final_processed_video_url'] = final_video_url
                
                return Response(serializer_data)
            else:
                error_msg = result.get('error', 'Unknown error')
                # Provide more helpful error messages
                if 'timeout' in error_msg.lower() or 'timed out' in error_msg.lower():
                    error_msg = f"Transcription timed out: {error_msg}. The video may be too long. Try a shorter video or wait longer."
                elif 'memory' in error_msg.lower() or 'out of memory' in error_msg.lower():
                    error_msg = f"Insufficient memory: {error_msg}. Try using a smaller Whisper model or processing a shorter video."
                elif not error_msg or error_msg == 'Unknown error':
                    error_msg = "Transcription failed. Please check if the video file is valid and contains audio."
                
                video.transcription_status = 'failed'
                video.transcript_error_message = error_msg
                video.save()

                return Response({
                    "status": "failed",
                    "error": error_msg,
                    "step": "transcription"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            import traceback
            error_details = str(e)
            print(f"Transcription exception: {error_details}")
            traceback.print_exc()
            
            # Check if it's a "no audio stream" error
            if 'no audio stream' in error_details.lower() or 'video-only' in error_details.lower():
                video.transcription_status = 'skipped'
                video.transcript_error_message = 'Video has no audio stream - transcription skipped'
                video.save()
                return Response({
                    "status": "skipped",
                    "message": "Video has no audio stream. Transcription skipped. You can still process other steps if you have an existing transcript.",
                    "error": error_details,
                    "step": "transcription",
                    "video_id": video.id
                }, status=status.HTTP_200_OK)
            
            # Provide more detailed error message
            if 'whisper' in error_details.lower():
                error_details = f"Whisper transcription error: {error_details}. Please check if Whisper is properly installed."
            elif 'ffmpeg' in error_details.lower():
                error_details = f"FFmpeg error: {error_details}. Please ensure ffmpeg is installed."
            elif 'file' in error_details.lower() or 'not found' in error_details.lower():
                error_details = f"File error: {error_details}. Please ensure the video file exists."
            elif 'timeout' in error_details.lower() or 'timed out' in error_details.lower():
                error_details = f"Transcription timed out: {error_details}. The video may be too long. Try a shorter video or increase timeout settings."
            elif 'memory' in error_details.lower() or 'out of memory' in error_details.lower():
                error_details = f"Insufficient memory: {error_details}. Try using a smaller Whisper model or processing a shorter video."
            else:
                error_details = f"Transcription failed: {error_details}"
            
            video.transcription_status = 'failed'
            video.transcript_error_message = error_details
            video.save()

            return Response({
                "status": "failed",
                "error": error_details,
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
    def reset_transcription(self, request, pk=None):
        """Reset stuck transcription status"""
        video = self.get_object()
        
        if video.transcription_status == 'transcribing':
            elapsed_minutes = 0
            if video.transcript_started_at:
                elapsed_minutes = (timezone.now() - video.transcript_started_at).total_seconds() / 60
            
            # Reset transcription status
            video.transcription_status = 'not_transcribed'
            video.transcript_started_at = None
            video.transcript_error_message = f"Transcription was reset after {elapsed_minutes:.1f} minutes"
            video.save()
            
            return Response({
                "status": "success",
                "message": f"Transcription reset successfully (was running for {elapsed_minutes:.1f} minutes)",
                "elapsed_minutes": elapsed_minutes
            })
        else:
            return Response({
                "status": "error",
                "message": "Video is not currently transcribing"
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def synthesize(self, request, pk=None):
        """Synthesize audio using Google TTS (Gemini TTS) - no voice profile required"""
        video = self.get_object()
        
        # Check if video has Hindi script or transcript
        if not video.hindi_script and not video.transcript:
            return Response({
                "status": "error",
                "error": "No Hindi script or transcript available. Please transcribe the video first."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if already synthesizing
        if video.synthesis_status == 'synthesizing':
            return Response({
                "status": "already_processing",
                "message": "Audio synthesis is already in progress"
            }, status=status.HTTP_200_OK)
        
        try:
            video.synthesis_status = 'synthesizing'
            video.save()
            
            from .utils import get_clean_script_for_tts
            
            # Use Hindi script if available, otherwise use transcript
            script_to_use = video.hindi_script if video.hindi_script else video.transcript
            clean_script = get_clean_script_for_tts(script_to_use)
            
            if not clean_script:
                video.synthesis_status = 'failed'
                video.synthesis_error = "No script text available for synthesis"
                video.save()
                return Response({
                    "status": "error",
                    "error": "No script text available for synthesis"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Use Gemini TTS service (Google TTS)
            from .gemini_tts_service import GeminiTTSService, GEMINI_TTS_AVAILABLE
            import tempfile
            import os
            
            if not GEMINI_TTS_AVAILABLE:
                error_msg = "Gemini TTS service not available"
                logger.error(error_msg)
                video.synthesis_status = 'failed'
                video.synthesis_error = error_msg
                video.save()
                return Response({
                    "status": "error",
                    "error": error_msg
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            # Get Gemini API key from AIProviderSettings
            from .models import AIProviderSettings
            settings_obj = AIProviderSettings.objects.first()
            api_key = settings_obj.get_api_key('gemini') if settings_obj else None
            
            if not api_key:
                error_msg = "Gemini API key not configured. Please set it in AI Provider Settings."
                video.synthesis_status = 'failed'
                video.synthesis_error = error_msg
                video.save()
                return Response({
                    "status": "error",
                    "error": error_msg
                }, status=status.HTTP_400_BAD_REQUEST)
            
            service = GeminiTTSService(api_key=api_key)
            
            # Create temp audio file (Gemini TTS generates MP3)
            temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            temp_audio_path = temp_audio.name
            temp_audio.close()
            
            # Get TTS settings from video model
            tts_temperature = video.tts_temperature if video.tts_temperature else 0.75
            
            # Use Enceladus voice for Hindi (as specified in n8n workflow)
            voice_name = 'Enceladus'
            language_code = 'hi-IN'  # Hindi (India)
            
            # Let GeminiTTSService generate comprehensive style prompt automatically
            # It will analyze content and create optimal prompt with all best practices
            style_prompt = None  # Let service generate comprehensive prompt
            
            # Generate TTS audio using Gemini TTS
            print(f"Generating TTS with Gemini TTS (voice: {voice_name}, language: {language_code}, temp: {tts_temperature})...")
            service.generate_speech(
                text=clean_script,
                language_code=language_code,
                voice_name=voice_name,
                output_path=temp_audio_path,
                temperature=tts_temperature,
                style_prompt=style_prompt
            )
            
            # Check audio duration and adjust if needed
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
                        print(f"✓ TTS audio duration ({audio_duration:.2f}s) matches video duration ({video.duration:.2f}s)")
            
            # Save audio file (Gemini TTS generates MP3)
            from django.core.files import File
            with open(temp_audio_path, 'rb') as f:
                video.synthesized_audio.save(f"synthesized_audio_{video.pk}.mp3", File(f), save=False)
            
            video.synthesis_status = 'synthesized'
            video.synthesis_error = ''
            video.synthesized_at = timezone.now()
            video.save()
            
            # Clean up temp file
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
            
            print(f"✓ Gemini TTS audio generated successfully for video {video.pk} (voice: {voice_name})")
            
            return Response({
                "status": "success",
                "message": "Audio synthesized successfully using Google TTS (Gemini)",
                "synthesized_audio_url": request.build_absolute_uri(video.synthesized_audio.url) if video.synthesized_audio else None
            })
            
        except Exception as e:
            error_msg = f"TTS synthesis failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            video.synthesis_status = 'failed'
            video.synthesis_error = error_msg
            video.save()
            
            return Response({
                "status": "error",
                "error": error_msg
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def process_ai(self, request, pk=None):
        """Process video with AI"""
        video = self.get_object()

        # Check if transcription is required first
        if video.transcription_status != 'transcribed' and not video.transcript:
            return Response({
                "status": "failed",
                "error": "Video must be transcribed before AI processing. Please transcribe the video first.",
                "requires_transcription": True
            }, status=status.HTTP_400_BAD_REQUEST)

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
                error_msg = result.get('error', 'Unknown error')
                # Provide more helpful error messages
                if 'No title, description, or transcript' in error_msg:
                    error_msg = "Cannot process: Video has no transcript, title, or description. Please ensure the video is transcribed first."
                elif 'API' in error_msg or 'api_key' in error_msg.lower():
                    error_msg = f"AI API error: {error_msg}. Please check your AI provider settings and API key."
                
                video.ai_processing_status = 'failed'
                video.ai_error_message = error_msg
                video.save()

                return Response({
                    "status": "failed",
                    "error": error_msg
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            import traceback
            error_details = str(e)
            print(f"AI processing exception: {error_details}")
            traceback.print_exc()
            
            # Provide more detailed error message
            if 'API' in error_details or 'api_key' in error_details.lower():
                error_details = f"AI API error: {error_details}. Please check your AI provider settings."
            elif 'transcript' in error_details.lower():
                error_details = f"Transcript error: {error_details}. Please ensure the video is transcribed first."
            else:
                error_details = f"AI processing failed: {error_details}"
            
            video.ai_processing_status = 'failed'
            video.ai_error_message = error_details
            video.save()

            return Response({
                "status": "failed",
                "error": error_details
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
    def upload_and_sync(self, request, pk=None):
        """Manually trigger Cloudinary upload and Google Sheets sync for an existing video"""
        try:
            video = self.get_object()
            
            if not video.final_processed_video and not video.final_processed_video_url:
                return Response({
                    "error": "Video has no final processed video. Please process the video first."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            results = {
                'metadata_generated': False,
                'cloudinary_uploaded': False,
                'google_sheets_synced': False,
                'errors': []
            }
            
            # Generate metadata if not already generated
            if not video.generated_title or not video.generated_description:
                try:
                    metadata_result = generate_video_metadata(video)
                    if metadata_result.get('status') == 'success':
                        video.generated_title = metadata_result.get('title', '')
                        video.generated_description = metadata_result.get('description', '')
                        video.generated_tags = metadata_result.get('tags', '')
                        results['metadata_generated'] = True
                        print(f"✓ Generated metadata: {video.generated_title[:50]}...")
                    else:
                        results['errors'].append(f"Metadata generation failed: {metadata_result.get('error', 'Unknown error')}")
                except Exception as e:
                    results['errors'].append(f"Metadata generation error: {str(e)}")
            
            # Upload to Cloudinary if enabled (always upload/replace to ensure latest version)
            try:
                if upload_video_file:
                    # Use video_id as public_id to replace existing video
                    video_id_for_cloudinary = video.video_id or str(video.id)
                    cloudinary_result = upload_video_file(
                        video.final_processed_video,
                        video_id=video_id_for_cloudinary
                    )
                    if cloudinary_result:
                        video.cloudinary_url = cloudinary_result.get('secure_url') or cloudinary_result.get('url', '')
                        video.cloudinary_uploaded_at = timezone.now()
                        results['cloudinary_uploaded'] = True
                        print(f"✓ Uploaded to Cloudinary (replaced if exists): {video.cloudinary_url[:50]}...")
                    else:
                        results['errors'].append("Cloudinary upload failed (no result returned)")
                else:
                    results['errors'].append("Cloudinary upload skipped (cloudinary package not installed)")
            except Exception as e:
                results['errors'].append(f"Cloudinary upload error: {str(e)}")
            
            # Save video with any updates
            video.save()
            
            # Add/Update to Google Sheets if enabled (always sync to ensure latest data)
            # Run in background thread to prevent blocking
            def sync_to_sheets_background():
                """Background task to sync video to Google Sheets"""
                try:
                    if add_video_to_sheet:
                        logger.info(f"Starting Google Sheets sync for video {video.id} in background thread")
                        sheet_result = add_video_to_sheet(video, video.cloudinary_url)
                        if sheet_result and sheet_result.get('success'):
                            logger.info(f"✓ Successfully synced video {video.id} to Google Sheets")
                        else:
                            error_msg = sheet_result.get('error', 'Unknown error') if sheet_result else 'Google Sheets not configured'
                            logger.warning(f"Google Sheets sync failed for video {video.id}: {error_msg}")
                    else:
                        logger.warning(f"Google Sheets sync skipped for video {video.id}: not configured")
                except Exception as e:
                    logger.error(f"Google Sheets sync error for video {video.id}: {str(e)}", exc_info=True)
            
            # Start background thread for Google Sheets sync (non-blocking)
            if add_video_to_sheet:
                import threading
                sync_thread = threading.Thread(target=sync_to_sheets_background, daemon=True)
                sync_thread.start()
                results['google_sheets_synced'] = True  # Background sync started successfully
                logger.info(f"Google Sheets sync started in background for video {video.id}")
            else:
                results['errors'].append('Google Sheets sync failed: not configured')
            
            # Determine overall status
            success_count = sum([
                results['metadata_generated'],
                results['cloudinary_uploaded'],
                results['google_sheets_synced']
            ])
            
            if success_count > 0:
                return Response({
                    "status": "success",
                    "message": f"Completed {success_count} operation(s)",
                    **results
                })
            else:
                return Response({
                    "status": "partial",
                    "message": "No new operations completed",
                    **results
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            return Response({
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def reprocess(self, request, pk=None):
        """Reprocess video - reset processing state and re-run the full pipeline"""
        video = self.get_object()
        
        if not video.is_downloaded and not video.video_url:
            return Response({
                "error": "Video must be downloaded or have a video URL to reprocess"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if video is currently being processed
        force_reprocess = request.data.get('force', False) or request.query_params.get('force', 'false').lower() == 'true'
        
        if not force_reprocess and (video.transcription_status == 'transcribing' or 
            video.ai_processing_status == 'processing' or
            video.script_status == 'generating' or
            video.synthesis_status == 'synthesizing'):
            return Response({
                "error": "Video is currently being processed. Please wait for current process to complete.",
                "can_force": True
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Smart Resume: Check which steps are already complete and only reset failed/pending steps
            # This saves time by not redoing work that's already done
            
            # Determine which steps are complete
            transcription_complete = (
                video.transcription_status == 'transcribed' and 
                video.transcript and 
                video.transcript_without_timestamps
            )
            
            ai_processing_complete = (
                video.ai_processing_status == 'processed' and 
                video.ai_summary
            )
            
            script_generation_complete = (
                video.script_status == 'generated' and 
                video.hindi_script
            )
            
            tts_synthesis_complete = (
                video.synthesis_status == 'synthesized' and 
                video.synthesized_audio
            )
            
            # Determine where to start processing
            start_from_step = None
            
            if not transcription_complete:
                start_from_step = 'transcription'
                # Reset transcription and all subsequent steps
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
                video.script_edited = False
                video.script_edited_at = None
                
                video.synthesis_status = 'not_synthesized'
                video.synthesis_error = ''
                if video.synthesized_audio:
                    try:
                        video.synthesized_audio.delete(save=False)
                    except Exception:
                        pass
                    video.synthesized_audio = None
                
                # Delete processed video files
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
                
            elif not ai_processing_complete:
                start_from_step = 'ai_processing'
                # Reset AI processing and all subsequent steps
                video.ai_processing_status = 'not_processed'
                video.ai_summary = ''
                video.ai_tags = ''
                video.ai_processed_at = None
                video.ai_error_message = ''
                
                video.script_status = 'not_generated'
                video.hindi_script = ''
                video.script_error_message = ''
                video.script_generated_at = None
                video.script_edited = False
                video.script_edited_at = None
                
                video.synthesis_status = 'not_synthesized'
                video.synthesis_error = ''
                if video.synthesized_audio:
                    try:
                        video.synthesized_audio.delete(save=False)
                    except Exception:
                        pass
                    video.synthesized_audio = None
                
                # Delete processed video files
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
                
            elif not script_generation_complete:
                start_from_step = 'script_generation'
                # Reset script generation and all subsequent steps
                video.script_status = 'not_generated'
                video.hindi_script = ''
                video.script_error_message = ''
                video.script_generated_at = None
                video.script_edited = False
                video.script_edited_at = None
                
                video.synthesis_status = 'not_synthesized'
                video.synthesis_error = ''
                if video.synthesized_audio:
                    try:
                        video.synthesized_audio.delete(save=False)
                    except Exception:
                        pass
                    video.synthesized_audio = None
                
                # Delete processed video files
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
                
            elif not tts_synthesis_complete:
                start_from_step = 'tts_synthesis'
                # Reset TTS synthesis and video processing
                video.synthesis_status = 'not_synthesized'
                video.synthesis_error = ''
                if video.synthesized_audio:
                    try:
                        video.synthesized_audio.delete(save=False)
                    except Exception:
                        pass
                    video.synthesized_audio = None
                
                # Delete processed video files
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
                
            else:
                # All steps complete, just reset video processing
                start_from_step = 'video_processing'
                # Delete processed video files
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
            
            # Trigger the full transcription pipeline in a background thread
            # This ensures the request doesn't timeout while processing
            import threading
            
            def run_pipeline():
                try:
                    print(f"🔄 Starting reprocess pipeline for video {video.id} in background thread")
                    
                    # Set status to transcribing
                    video.transcription_status = 'transcribing'
                    video.transcript_started_at = timezone.now()
                    video.save()
                    
                    # Call transcribe_video
                    result = transcribe_video(video)
                    
                    # Handle dual transcription results (returns different structure)
                    if result.get('status') in ['success', 'partial'] and ('whisper_result' in result or 'nca_result' in result):
                        # Dual transcription mode - extract the best result
                        video.refresh_from_db()
                        
                        if result.get('whisper_result') and result['whisper_result'].get('status') == 'success':
                            # Use Whisper result - it's already saved to video.whisper_transcript fields
                            result = {
                                'status': 'success',
                                'text': video.whisper_transcript_without_timestamps or result['whisper_result'].get('text', ''),
                                'transcript_with_timestamps': video.whisper_transcript or '',
                                'transcript_without_timestamps': video.whisper_transcript_without_timestamps or '',
                                'text_hindi': video.whisper_transcript_hindi or '',
                                'language': video.whisper_transcript_language or '',
                                'srt': '',
                                'segments': result['whisper_result'].get('segments', [])
                            }
                            # Update main transcript fields from Whisper
                            video.transcription_status = 'transcribed'
                            video.transcript = video.whisper_transcript
                            video.transcript_without_timestamps = video.whisper_transcript_without_timestamps
                            video.transcript_hindi = video.whisper_transcript_hindi
                            video.transcript_language = video.whisper_transcript_language
                            video.transcript_processed_at = timezone.now()
                            video.save()
                        elif result.get('nca_result') and result['nca_result'].get('status') == 'success':
                            # Use NCA result - it's already saved to video.transcript fields
                            result = {
                                'status': 'success',
                                'text': video.transcript_without_timestamps or result['nca_result'].get('text', ''),
                                'transcript_with_timestamps': video.transcript or '',
                                'transcript_without_timestamps': video.transcript_without_timestamps or '',
                                'text_hindi': video.transcript_hindi or '',
                                'language': video.transcript_language or '',
                                'srt': result['nca_result'].get('srt', ''),
                                'segments': result['nca_result'].get('segments', [])
                            }
                        else:
                            # Both failed
                            error_msg = "Both NCA and Whisper transcription failed"
                            if result.get('whisper_result'):
                                error_msg = result['whisper_result'].get('error', error_msg)
                            elif result.get('nca_result'):
                                error_msg = result['nca_result'].get('error', error_msg)
                            result = {
                                'status': 'failed',
                                'error': error_msg
                            }
                    
                    if result.get('status') == 'success':
                        # Refresh video to get latest data (dual transcription may have already saved it)
                        video.refresh_from_db()
                        
                        # Only update if not already set (dual transcription may have already saved to video)
                        if not video.transcript or video.transcription_status != 'transcribed':
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
                                from .utils import translate_text_with_ai
                                print(f"Translating transcript to Hindi using AI (preserves meaning) (language: {result.get('language', 'unknown')})...")
                                hindi_transcript = translate_text_with_ai(transcript_without_timestamps, target='hi')
                            
                            video.transcript_hindi = hindi_transcript
                            video.transcript_language = result.get('language', '')
                            video.transcription_status = 'transcribed'
                            video.transcript_processed_at = timezone.now()
                            video.transcript_error_message = ''
                            video.save()
                        else:
                            print(f"✓ Transcript already saved by dual transcription, using existing data")
                        
                        # Continue with AI processing, script generation, TTS, and video processing
                        # This is the same logic as in the transcribe action
                        try:
                            # Set status to processing and ensure it's committed to database immediately
                            # Refresh from DB to get latest state, then update and save
                            video.refresh_from_db()
                            video.ai_processing_status = 'processing'
                            # Save with update_fields for efficiency and to ensure commit
                            video.save(update_fields=['ai_processing_status'])
                            # Log the status update for debugging
                            print(f"✓ AI Processing status set to 'processing' for video {video.id} (saved to DB)")
                            
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
                            
                            # Generate script with timeout protection
                            import threading
                            import queue
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
                                # Script generation timed out
                                error_msg = "Script generation timed out after 5 minutes"
                                print(f"✗ {error_msg}")
                                video.script_status = 'failed'
                                video.script_error_message = error_msg
                                video.save()
                            elif not exception_queue.empty():
                                # Exception occurred
                                e = exception_queue.get()
                                error_msg = f"Script generation error: {str(e)}"
                                print(f"✗ {error_msg}")
                                import traceback
                                traceback.print_exc()
                                video.script_status = 'failed'
                                video.script_error_message = error_msg
                                video.save()
                            elif not script_queue.empty():
                                # Script generation completed
                                script_result = script_queue.get()
                                
                                if script_result['status'] == 'success':
                                    video.hindi_script = script_result['script']
                                    video.script_status = 'generated'
                                    video.script_generated_at = timezone.now()
                                    video.script_error_message = ''
                                    video.save()
                                    print(f"✓ Hindi script generated successfully")
                                else:
                                    video.script_status = 'failed'
                                    video.script_error_message = script_result.get('error', 'Unknown error')
                                    video.save()
                                    print(f"✗ Script generation failed: {script_result.get('error', 'Unknown error')}")
                            else:
                                # No result - something went wrong
                                error_msg = "Script generation completed but no result was returned"
                                print(f"✗ {error_msg}")
                                video.script_status = 'failed'
                                video.script_error_message = error_msg
                                video.save()
                        except Exception as e:
                            print(f"Script generation error during reprocess: {e}")
                            import traceback
                            traceback.print_exc()
                            video.script_status = 'failed'
                            video.script_error_message = str(e)
                            video.save()
                        
                        # Step 4: Script Generation Complete - PAUSE for User Review
                        # NEW WORKFLOW: After script generation, pause and wait for user to edit/approve
                        # Fix: If script exists but status is still 'generating', update status to 'generated'
                        if video.hindi_script and video.script_status == 'generating':
                            print(f"⚠ Script exists but status is 'generating' - fixing status to 'generated'")
                            video.script_status = 'generated'
                            if not video.script_generated_at:
                                video.script_generated_at = timezone.now()
                            video.save()
                        
                        # CRITICAL: Check if script needs user review (not yet edited)
                        if video.script_status == 'generated' and video.hindi_script and not video.script_edited:
                            # Ensure script_edited is explicitly False
                            video.script_edited = False
                            video.save()
                            print(f"✓ Script generated - PAUSED for user review/editing")
                            print(f"   Script status: {video.script_status}")
                            print(f"   Script edited: {video.script_edited}")
                            print(f"   User must save script (via /update_script/) to continue to TTS")
                            # EXIT THREAD - don't automatically proceed to TTS
                            # Frontend will poll and detect script_status='generated' + script_edited=False
                            # and show the script editor modal
                            return  # Exit the thread gracefully
                        
                        
                        # If script was already edited (reprocessing after editing), continue with TTS
                        if video.script_status == 'generated' and video.hindi_script and video.script_edited:
                            try:
                                video.synthesis_status = 'synthesizing'
                                video.save()
                                
                                from .utils import get_clean_script_for_tts
                                clean_script = get_clean_script_for_tts(video.hindi_script)
                                
                                # Use Gemini TTS service for TTS generation
                                from .gemini_tts_service import GeminiTTSService, GEMINI_TTS_AVAILABLE
                                import tempfile
                                import os
                                
                                if not GEMINI_TTS_AVAILABLE:
                                    logger.error("Gemini TTS not available")
                                    video.synthesis_status = 'failed'
                                    video.synthesis_error = 'Gemini TTS service not available'
                                    video.save()
                                else:
                                    try:
                                        # Get Gemini API key from AIProviderSettings
                                        from .models import AIProviderSettings
                                        settings_obj = AIProviderSettings.objects.first()
                                        api_key = settings_obj.get_api_key('gemini') if settings_obj else None
                                        
                                        if not api_key:
                                            raise Exception("Gemini API key not configured. Please set it in AI Provider Settings.")
                                        
                                        service = GeminiTTSService(api_key=api_key)
                                        
                                        # Create temp audio file (Gemini TTS generates MP3)
                                        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                                        temp_audio_path = temp_audio.name
                                        temp_audio.close()
                                        
                                        # Get TTS settings from video model
                                        tts_temperature = video.tts_temperature if video.tts_temperature else 0.75
                                        
                                        # Use Enceladus voice for Hindi (as specified in n8n workflow)
                                        voice_name = 'Enceladus'
                                        language_code = 'hi-IN'  # Hindi (India)
                                        
                                        # Let GeminiTTSService generate comprehensive style prompt automatically
                                        # It will analyze content and create optimal prompt with all best practices
                                        style_prompt = None  # Let service generate comprehensive prompt
                                        
                                        print(f"Generating TTS with Gemini TTS (voice: {voice_name}, language: {language_code}, temp: {tts_temperature})...")
                                        
                                        # Generate speech using correct parameter names
                                        service.generate_speech(
                                            text=clean_script,
                                            language_code=language_code,
                                            voice_name=voice_name,
                                            output_path=temp_audio_path,
                                            temperature=tts_temperature,
                                            style_prompt=style_prompt
                                        )
                                        
                                        # Save to video model
                                        from django.core.files import File
                                        with open(temp_audio_path, 'rb') as f:
                                            video.synthesized_audio.save(f"synthesized_{video.pk}.mp3", File(f), save=False)
                                        
                                        # Note: synthesized_audio_url will be generated by serializer if needed
                                        # Don't set it here in background thread (request not available)
                                        
                                        video.synthesis_status = 'synthesized'
                                        video.synthesis_error = ''
                                        video.synthesized_at = timezone.now()
                                        video.save()
                                        
                                        print(f"✓ Gemini TTS audio generated successfully for video {video.pk} (voice: {voice_name})")
                                        
                                        # Clean up temp file
                                        if os.path.exists(temp_audio_path):
                                            os.unlink(temp_audio_path)
                                        
                                        print(f"✓ Gemini TTS audio generated successfully for video {video.pk} (voice: {voice_name})")
                                    except Exception as tts_error:
                                        error_msg = f"XTTS generation failed: {str(tts_error)}"
                                        logger.error(error_msg, exc_info=True)
                                        video.synthesis_status = 'failed'
                                        video.synthesis_error = error_msg
                                        video.save()
                                        print(f"✗ {error_msg}")
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
                                            
                                            # Update status to removing_audio
                                            video.final_video_status = 'removing_audio'
                                            video.final_video_error = ''
                                            video.save(update_fields=['final_video_status', 'final_video_error'])
                                            
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
                                            
                                            ffmpeg_result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                                            if ffmpeg_result.returncode == 0 and os.path.exists(temp_no_audio_path):
                                                # Save voice-removed video
                                                from django.core.files import File
                                                with open(temp_no_audio_path, 'rb') as f:
                                                    video.voice_removed_video.save(f"voice_removed_{video.pk}.mp4", File(f), save=False)
                                                # Note: voice_removed_video_url will be generated by serializer if needed
                                                # Don't set it here in background thread (request not available)
                                                video.save()
                                                print(f"✓ Step 5a (ffmpeg) completed: Voice removed video saved")
                                                
                                                # Clean up temp file
                                                os.unlink(temp_no_audio_path)
                                                
                                                # Use the saved file for next step
                                                voice_removed_file_path = video.voice_removed_video.path
                                                
                                                # Update status to combining_audio
                                                video.final_video_status = 'combining_audio'
                                                video.save(update_fields=['final_video_status'])
                                                
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
                                                        '-c:v', 'copy',  # Copy video stream
                                                        '-c:a', 'aac',   # Encode audio to AAC
                                                        '-map', '0:v:0', # Map first video stream from first input
                                                        '-map', '1:a:0', # Map first audio stream from second input
                                                        '-shortest',     # Stop when shortest input ends
                                                        '-y',            # Overwrite output
                                                        temp_final_path
                                                    ]
                                                    
                                                    ffmpeg_result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                                                    
                                                    if ffmpeg_result.returncode == 0 and os.path.exists(temp_final_path):
                                                        # Save final video
                                                        from django.core.files import File
                                                        with open(temp_final_path, 'rb') as f:
                                                            video.final_processed_video.save(f"final_{video.pk}.mp4", File(f), save=False)
                                                        
                                                        # Note: final_processed_video_url will be generated by serializer if needed
                                                        # Don't set it here in background thread (request not available)
                                                        
                                                        # Upload to Cloudinary if configured
                                                        if upload_video_file:
                                                            try:
                                                                print(f"Uploading final video to Cloudinary...")
                                                                cloudinary_url = upload_video_file(video.final_processed_video.path, folder="rednote_final")
                                                                if cloudinary_url:
                                                                    video.cloudinary_url = cloudinary_url
                                                                    video.cloudinary_uploaded_at = timezone.now()
                                                                    print(f"✓ Uploaded to Cloudinary: {cloudinary_url}")
                                                            except Exception as e:
                                                                print(f"Cloudinary upload failed: {e}")
                                                        
                                                        # Sync to Google Sheets if configured
                                                        if add_video_to_sheet:
                                                            try:
                                                                print(f"Syncing to Google Sheets...")
                                                                success = add_video_to_sheet(video)
                                                                if success:
                                                                    video.google_sheets_synced = True
                                                                    video.google_sheets_synced_at = timezone.now()
                                                                    print(f"✓ Synced to Google Sheets")
                                                            except Exception as e:
                                                                print(f"Google Sheets sync failed: {e}")
                                                        
                                                        # Update final_video_status to completed
                                                        video.final_video_status = 'completed'
                                                        video.final_video_error = ''
                                                        video.save()
                                                        print(f"✓ Step 5b (ffmpeg) completed: Final video saved")
                                                        
                                                        # Clean up temp file
                                                        os.unlink(temp_final_path)
                                                    else:
                                                        print(f"✗ ffmpeg merge failed: {ffmpeg_result.stderr}")
                                                        video.final_video_status = 'failed'
                                                        video.final_video_error = f"ffmpeg merge failed: {ffmpeg_result.stderr}"
                                                        video.synthesis_error = f"ffmpeg merge failed: {ffmpeg_result.stderr}"
                                                        video.save()
                                                else:
                                                    print("✗ TTS audio file missing for merge")
                                            else:
                                                print(f"✗ ffmpeg audio removal failed: {ffmpeg_result.stderr}")
                                                video.final_video_status = 'failed'
                                                video.final_video_error = f"ffmpeg audio removal failed: {ffmpeg_result.stderr}"
                                                video.synthesis_error = f"ffmpeg audio removal failed: {ffmpeg_result.stderr}"
                                                video.save()
                                except Exception as e:
                                    error_msg = f"ffmpeg processing error: {str(e)}"
                                    print(f"✗ {error_msg}")
                                    import traceback
                                    traceback.print_exc()
                                    video.final_video_status = 'failed'
                                    video.final_video_error = error_msg
                                    video.synthesis_error = error_msg
                                    video.save()
                        else:
                            if video.synthesis_status != 'synthesized':
                                print(f"⚠ TTS not synthesized yet (status: {video.synthesis_status}), skipping audio replacement")
                            if not video.synthesized_audio:
                                print(f"⚠ No synthesized audio available, skipping audio replacement")
                    else:
                        # Transcription failed
                        error_msg = result.get('error', 'Unknown error')
                        if not error_msg or error_msg == 'Unknown error':
                            # Try to get more specific error information
                            if 'segments' in result and not result.get('segments'):
                                error_msg = 'Transcription completed but no segments were generated. The audio may be too short or contain no speech.'
                            elif 'language' in result and not result.get('language'):
                                error_msg = 'Could not detect language in the audio. Please ensure the video contains clear speech.'
                            else:
                                error_msg = 'Transcription failed. Please check if the video file is valid and contains audio.'
                        
                        video.transcription_status = 'failed'
                        video.transcript_error_message = error_msg
                        video.save()
                        print(f"✗ Transcription failed: {error_msg}")
                except Exception as e:
                    import traceback
                    error_details = str(e)
                    print(f"Pipeline error during reprocess: {error_details}")
                    traceback.print_exc()
                    
                    # Provide more detailed error message
                    if 'whisper' in error_details.lower():
                        error_details = f"Whisper transcription error: {error_details}. Please check if Whisper is properly installed."
                    elif 'ffmpeg' in error_details.lower():
                        error_details = f"FFmpeg error: {error_details}. Please ensure ffmpeg is installed."
                    elif 'file' in error_details.lower() or 'not found' in error_details.lower():
                        error_details = f"File error: {error_details}. Please ensure the video file exists."
                    else:
                        error_details = f"Processing failed: {error_details}"
                    
                    # Update video status based on where the error occurred
                    video.refresh_from_db()
                    if video.transcription_status == 'transcribing':
                        video.transcription_status = 'failed'
                        video.transcript_error_message = error_details
                    elif video.ai_processing_status == 'processing':
                        video.ai_processing_status = 'failed'
                        video.ai_error_message = error_details
                    elif video.script_status == 'generating':
                        video.script_status = 'failed'
                        video.script_error_message = error_details
                    elif video.synthesis_status == 'synthesizing':
                        video.synthesis_status = 'failed'
                        video.synthesis_error = error_details
                    video.save()
            
            # Start the pipeline in a background thread
            pipeline_thread = threading.Thread(target=run_pipeline, daemon=True)
            pipeline_thread.start()
            
            return Response({
                "status": "processing_started",
                "message": "Reprocessing started in background",
                "video_id": video.id
            })
            
        except Exception as e:
            print(f"Error during reprocess setup: {e}")
            import traceback
            traceback.print_exc()
            return Response({
                "status": "failed",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @action(detail=True, methods=['post'])
    def update_script(self, request, pk=None):
        """
        Update Hindi script after user editing
        
        This endpoint allows users to edit the generated script before TTS synthesis.
        The workflow pauses after script generation to allow manual editing.
        """
        video = self.get_object()
        
        # Get edited script from request
        edited_script = request.data.get('hindi_script', '')
        
        if not edited_script or not edited_script.strip():
            return Response({
                'error': 'Script cannot be empty'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Save edited script
        video.hindi_script = edited_script.strip()
        video.script_status = 'generated'  # Mark as ready for TTS
        video.script_edited = True  # Track that it was manually edited
        video.script_edited_at = timezone.now()
        video.save()
        
        logger.info(f"Script updated for video {video.pk} by user")
        
        return Response({
            'message': 'Script updated successfully',
            'hindi_script': edited_script.strip(),
            'script_edited': True,
            'script_edited_at': video.script_edited_at
        })


    @action(detail=True, methods=['post'])
    def synthesize_tts(self, request, pk=None):
        """
        Trigger TTS synthesis after script editing
        
        Automatically adjusts TTS speed to match video duration.
        This endpoint is called after the user edits and saves the script.
        """
        video = self.get_object()
        
        # Validate prerequisites
        if not video.hindi_script or not video.hindi_script.strip():
            return Response({
                'error': 'No script available for synthesis'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if video.script_status != 'generated':
            return Response({
                'error': f'Script is not ready for synthesis (status: {video.script_status})'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate optimal TTS speed based on video duration
        optimal_speed = calculate_optimal_tts_speed(video)
        
        # Update TTS speed
        video.tts_speed = optimal_speed
        video.synthesis_status = 'synthesizing'
        video.save()
        
        logger.info(f"Starting TTS synthesis for video {video.pk} with speed {optimal_speed}x")
        
        # Start TTS synthesis in background thread
        import threading
        import queue
        
        synthesis_queue = queue.Queue()
        exception_queue = queue.Queue()
        
        def run_tts_synthesis():
            try:
                from .utils import get_clean_script_for_tts, enhance_script_with_tts_markup
                clean_script = get_clean_script_for_tts(video.hindi_script)
                
                # Check if script is already enhanced (contains markup tags)
                import re
                has_markup = bool(re.search(r'\[.*?\]', clean_script))
                
                if has_markup:
                    print(f"✓ Script already contains TTS markup tags (skipping re-enhancement)")
                    enhanced_script = clean_script
                else:
                    # CRITICAL: Enhance script with TTS markup tags for better audio quality
                    # This adds sound filters like [sigh], [laughing], [short pause], etc.
                    print(f"🎨 Enhancing script with AI-powered TTS markup tags...")
                    enhanced_script = enhance_script_with_tts_markup(clean_script)
                
                # Use Gemini TTS service for TTS generation
                from .gemini_tts_service import GeminiTTSService, GEMINI_TTS_AVAILABLE
                import tempfile
                import os
                
                if not GEMINI_TTS_AVAILABLE:
                    raise Exception("Gemini TTS service not available")
                
                # Get Gemini API key from AIProviderSettings
                from .models import AIProviderSettings
                settings_obj = AIProviderSettings.objects.first()
                api_key = settings_obj.get_api_key('gemini') if settings_obj else None
                
                if not api_key:
                    raise Exception("Gemini API key not configured. Please set it in AI Provider Settings.")
                
                service = GeminiTTSService(api_key=api_key)
                
                # Create temp audio file (Gemini TTS generates MP3)
                temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                temp_audio_path = temp_audio.name
                temp_audio.close()
                
                # Get TTS settings from video model
                tts_temperature = video.tts_temperature if video.tts_temperature else 0.75
                
                # Use Enceladus voice for Hindi (as specified in n8n workflow)
                voice_name = 'Enceladus'
                language_code = 'hi-IN'  # Hindi (India)
                
                # Let GeminiTTSService generate comprehensive style prompt automatically
                style_prompt = None  # Let service generate comprehensive prompt
                
                print(f"Generating TTS with Gemini TTS (voice: {voice_name}, language: {language_code}, speed: {optimal_speed}x, temp: {tts_temperature})...")
                
                # Generate speech with calculated speed using ENHANCED script with markup tags
                service.generate_speech(
                    text=enhanced_script,  # Use enhanced script with TTS markup tags!
                    language_code=language_code,
                    voice_name=voice_name,
                    output_path=temp_audio_path,
                    temperature=tts_temperature,
                    style_prompt=style_prompt,
                    speed_factor=optimal_speed  # Apply speed adjustment
                )
                
                # Save to video model
                from django.core.files import File
                with open(temp_audio_path, 'rb') as f:
                    video.synthesized_audio.save(f"synthesized_{video.pk}.mp3", File(f), save=False)
                
                video.synthesis_status = 'synthesized'
                video.synthesis_error = ''
                video.synthesized_at = timezone.now()
                video.save()
                
                # Clean up temp file
                if os.path.exists(temp_audio_path):
                    os.unlink(temp_audio_path)
                
                synthesis_queue.put({'status': 'success'})
                print(f"✓ TTS audio generated successfully for video {video.pk} at {optimal_speed}x speed")
                
            except Exception as e:
                exception_queue.put(e)
        
        # Start background thread
        synthesis_thread = threading.Thread(target=run_tts_synthesis, daemon=True)
        synthesis_thread.start()
        
        # Don't wait for completion - return immediately
        # Frontend will poll for status updates
        
        return Response({
            'message': 'TTS synthesis started',
            'tts_speed': optimal_speed,
            'synthesis_status': 'synthesizing'
        })


    @action(detail=True, methods=['delete', 'post'])
    def delete(self, request, pk=None):
        """Delete a video and all associated media files"""
        video = self.get_object()
        
        try:
            # Delete all associated media files
            files_deleted = []
            
            # Delete local_file
            if video.local_file:
                try:
                    video.local_file.delete(save=False)
                    files_deleted.append('local_file')
                except Exception as e:
                    logger.warning(f"Could not delete local_file: {e}")
            
            # Delete voice_removed_video
            if video.voice_removed_video:
                try:
                    video.voice_removed_video.delete(save=False)
                    files_deleted.append('voice_removed_video')
                except Exception as e:
                    logger.warning(f"Could not delete voice_removed_video: {e}")
            
            # Delete final_processed_video
            if video.final_processed_video:
                try:
                    video.final_processed_video.delete(save=False)
                    files_deleted.append('final_processed_video')
                except Exception as e:
                    logger.warning(f"Could not delete final_processed_video: {e}")
            
            # Delete synthesized_audio
            if video.synthesized_audio:
                try:
                    video.synthesized_audio.delete(save=False)
                    files_deleted.append('synthesized_audio')
                except Exception as e:
                    logger.warning(f"Could not delete synthesized_audio: {e}")
            
            # Delete from Cloudinary if public_id exists
            if upload_video_file and video.video_id:
                try:
                    from .cloudinary_service import get_cloudinary_config
                    import cloudinary.uploader
                    config = get_cloudinary_config()
                    if config:
                        cloudinary.config(
                            cloud_name=config['cloud_name'],
                            api_key=config['api_key'],
                            api_secret=config['api_secret']
                        )
                        public_id = f"videos/final/{video.video_id}"
                        cloudinary.uploader.destroy(public_id, resource_type='video')
                        logger.info(f"Deleted video from Cloudinary: {public_id}")
                        files_deleted.append('cloudinary_video')
                except Exception as e:
                    logger.warning(f"Could not delete from Cloudinary: {e}")
            
            # Delete from Google Sheets if synced
            if video.google_sheets_synced and add_video_to_sheet:
                try:
                    from .google_sheets_service import get_google_sheets_service
                    sheets_config = get_google_sheets_service()
                    if sheets_config:
                        service = sheets_config['service']
                        spreadsheet_id = sheets_config['spreadsheet_id']
                        sheet_name = sheets_config['sheet_name']
                        video_id = video.video_id or str(video.id)
                        
                        # Find and delete row with matching video_id
                        all_rows = service.spreadsheets().values().get(
                            spreadsheetId=spreadsheet_id,
                            range=f'{sheet_name}!A:J'
                        ).execute()
                        
                        if all_rows.get('values'):
                            for idx, row in enumerate(all_rows['values'], start=1):
                                if len(row) > 5 and row[5] == video_id:  # Column F (index 5) is Video ID
                                    # Delete the row
                                    service.spreadsheets().values().clear(
                                        spreadsheetId=spreadsheet_id,
                                        range=f'{sheet_name}!A{idx + 1}:J{idx + 1}'
                                    ).execute()
                                    # Shift rows up
                                    service.spreadsheets().batchUpdate(
                                        spreadsheetId=spreadsheet_id,
                                        body={
                                            'requests': [{
                                                'deleteDimension': {
                                                    'range': {
                                                        'sheetId': 0,  # Assuming first sheet
                                                        'dimension': 'ROWS',
                                                        'startIndex': idx,
                                                        'endIndex': idx + 1
                                                    }
                                                }
                                            }]
                                        }
                                    ).execute()
                                    logger.info(f"Deleted video from Google Sheets: row {idx + 1}")
                                    files_deleted.append('google_sheets_row')
                                    break
                except Exception as e:
                    logger.warning(f"Could not delete from Google Sheets: {e}")
            
            # Delete the video record
            video.delete()
            
            return Response({
                "status": "success",
                "message": "Video and all associated files deleted successfully",
                "files_deleted": files_deleted
            })
        except Exception as e:
            logger.error(f"Error deleting video {pk}: {e}", exc_info=True)
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
        # New fields
        gemini_api_key = request.data.get('gemini_api_key', '')
        openai_api_key = request.data.get('openai_api_key', '')
        script_generation_provider = request.data.get('script_generation_provider', 'gemini')
        default_provider = request.data.get('default_provider', 'gemini')
        
        # Legacy fields (optional, but good to keep populated for backward compatibility)
        provider = request.data.get('provider', default_provider)
        api_key = request.data.get('api_key', '')
        
        # If api_key is not provided but provider is, try to set it from the specific key
        if not api_key:
            if provider == 'gemini':
                api_key = gemini_api_key
            elif provider == 'openai':
                api_key = openai_api_key

        settings, created = AIProviderSettings.objects.get_or_create(id=1)

        settings.gemini_api_key = gemini_api_key
        settings.openai_api_key = openai_api_key
        settings.script_generation_provider = script_generation_provider
        settings.default_provider = default_provider
        
        # Update legacy fields
        settings.provider = provider
        settings.api_key = api_key
        
        settings.save()

        return Response({
            "status": "saved", 
            "provider": provider,
            "script_generation_provider": script_generation_provider,
            "default_provider": default_provider
        })


class CloudinarySettingsViewSet(viewsets.ViewSet):
    """ViewSet for Cloudinary Settings"""

    def list(self, request):
        """Get current Cloudinary settings"""
        settings = CloudinarySettings.objects.first()
        if not settings:
            return Response({
                "cloud_name": "",
                "api_key": "",
                "api_secret": "",
                "enabled": False
            })

        serializer = CloudinarySettingsSerializer(settings)
        return Response(serializer.data)

    def create(self, request):
        """Update Cloudinary settings"""
        cloud_name = request.data.get('cloud_name', '')
        api_key = request.data.get('api_key', '')
        api_secret = request.data.get('api_secret', '')
        enabled = request.data.get('enabled', False)

        settings, created = CloudinarySettings.objects.get_or_create(
            id=1,
            defaults={
                "cloud_name": cloud_name,
                "api_key": api_key,
                "api_secret": api_secret,
                "enabled": enabled
            }
        )

        if not created:
            settings.cloud_name = cloud_name
            settings.api_key = api_key
            settings.api_secret = api_secret
            settings.enabled = enabled
            settings.save()

        return Response({"status": "saved", "enabled": enabled})


class GoogleSheetsSettingsViewSet(viewsets.ViewSet):
    """ViewSet for Google Sheets Settings"""

    def list(self, request):
        """Get current Google Sheets settings"""
        settings = GoogleSheetsSettings.objects.first()
        if not settings:
            return Response({
                "spreadsheet_id": "",
                "sheet_name": "Sheet1",
                "credentials_json": "",
                "enabled": False
            })

        serializer = GoogleSheetsSettingsSerializer(settings)
        return Response(serializer.data)

    def create(self, request):
        """Update Google Sheets settings"""
        spreadsheet_id = request.data.get('spreadsheet_id', '')
        sheet_name = request.data.get('sheet_name', 'Sheet1')
        credentials_json = request.data.get('credentials_json', '')
        enabled = request.data.get('enabled', False)

        settings, created = GoogleSheetsSettings.objects.get_or_create(
            id=1,
            defaults={
                "spreadsheet_id": spreadsheet_id,
                "sheet_name": sheet_name,
                "credentials_json": credentials_json,
                "enabled": enabled
            }
        )

        if not created:
            settings.spreadsheet_id = spreadsheet_id
            settings.sheet_name = sheet_name
            settings.credentials_json = credentials_json
            settings.enabled = enabled
            settings.save()

        return Response({"status": "saved", "enabled": enabled})


class WatermarkSettingsViewSet(viewsets.ViewSet):
    """ViewSet for Watermark Settings"""

    def list(self, request):
        """Get current watermark settings"""
        settings = WatermarkSettings.objects.first()
        if not settings:
            return Response({
                "enabled": False,
                "watermark_text": "",
                "font_size": 24,
                "font_color": "white",
                "opacity": 0.7,
                "position_change_interval": 1.0
            })

        serializer = WatermarkSettingsSerializer(settings, context={'request': request})
        return Response(serializer.data)

    def create(self, request):
        """Update watermark settings"""
        enabled = request.data.get('enabled', False)
        watermark_text = request.data.get('watermark_text', '')
        font_size = int(request.data.get('font_size', 24))
        font_color = request.data.get('font_color', 'white')
        opacity = float(request.data.get('opacity', 0.7))
        position_change_interval = float(request.data.get('position_change_interval', 1.0))
        
        settings, created = WatermarkSettings.objects.get_or_create(
            id=1,
            defaults={
                "enabled": enabled,
                "watermark_text": watermark_text,
                "font_size": font_size,
                "font_color": font_color,
                "opacity": opacity,
                "position_change_interval": position_change_interval
            }
        )

        if not created:
            settings.enabled = enabled
            settings.watermark_text = watermark_text
            settings.font_size = font_size
            settings.font_color = font_color
            settings.opacity = opacity
            settings.position_change_interval = position_change_interval
        
        settings.save()

        serializer = WatermarkSettingsSerializer(settings, context={'request': request})
        return Response({"status": "saved", **serializer.data})


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def test_google_sheets(request):
    """Test endpoint for Google Sheets configuration"""
    from .google_sheets_service import get_google_sheets_service, ensure_header_row, extract_spreadsheet_id
    from .models import GoogleSheetsSettings
    import json
    
    results = {
        'success': False,
        'errors': [],
        'warnings': [],
        'info': {}
    }
    
    try:
        sheets_settings = GoogleSheetsSettings.objects.first()
        
        if not sheets_settings:
            results['errors'].append("Google Sheets settings not found. Please configure in Settings.")
            return Response(results, status=status.HTTP_400_BAD_REQUEST)
        
        results['info']['enabled'] = sheets_settings.enabled
        results['info']['has_spreadsheet_id'] = bool(sheets_settings.spreadsheet_id)
        results['info']['has_credentials'] = bool(sheets_settings.credentials_json)
        results['info']['sheet_name'] = sheets_settings.sheet_name
        
        if not sheets_settings.enabled:
            results['errors'].append("Google Sheets is disabled. Enable it in Settings.")
            return Response(results, status=status.HTTP_400_BAD_REQUEST)
        
        if not sheets_settings.spreadsheet_id:
            results['errors'].append("Spreadsheet ID is missing. Add it in Settings.")
            return Response(results, status=status.HTTP_400_BAD_REQUEST)
        
        if not sheets_settings.credentials_json:
            results['errors'].append("Service Account credentials are missing. Add them in Settings.")
            return Response(results, status=status.HTTP_400_BAD_REQUEST)
        
        # Test spreadsheet ID extraction
        extracted_id = extract_spreadsheet_id(sheets_settings.spreadsheet_id)
        results['info']['extracted_spreadsheet_id'] = extracted_id
        
        if not extracted_id:
            results['errors'].append("Could not extract spreadsheet ID from the provided value.")
            return Response(results, status=status.HTTP_400_BAD_REQUEST)
        
        # Test credentials JSON
        try:
            credentials_dict = json.loads(sheets_settings.credentials_json)
            results['info']['service_account_email'] = credentials_dict.get('client_email', 'N/A')
            results['info']['project_id'] = credentials_dict.get('project_id', 'N/A')
        except json.JSONDecodeError as e:
            results['errors'].append(f"Invalid JSON in credentials: {str(e)}")
            return Response(results, status=status.HTTP_400_BAD_REQUEST)
        
        # Test service creation
        sheets_config = get_google_sheets_service()
        if not sheets_config:
            results['errors'].append("Failed to create Google Sheets service. Check credentials.")
            return Response(results, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Test read access
        try:
            service = sheets_config['service']
            spreadsheet_id = sheets_config['spreadsheet_id']
            sheet_name = sheets_config['sheet_name']
            
            range_name = f'{sheet_name}!A1:J1'
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if values:
                results['info']['header_row'] = values[0]
            else:
                results['warnings'].append("No header row found. It will be created on first sync.")
            
        except Exception as e:
            error_str = str(e)
            service_account_email = credentials_dict.get('client_email', 'N/A')
            
            if 'PERMISSION_DENIED' in error_str or '403' in error_str or 'does not have permission' in error_str.lower():
                results['errors'].append(
                    f"❌ Permission Denied: The service account does not have access to the Google Sheet."
                )
                results['info']['service_account_email'] = service_account_email
                results['info']['fix_instructions'] = [
                    f"1. Open your Google Sheet: https://docs.google.com/spreadsheets/d/{extracted_id}/edit",
                    f"2. Click the 'Share' button (top right)",
                    f"3. Add this email address: {service_account_email}",
                    f"4. Give it 'Editor' access (not just Viewer)",
                    f"5. Click 'Send' or 'Done'",
                    f"6. Try testing the connection again"
                ]
            elif 'NOT_FOUND' in error_str or '404' in error_str:
                results['errors'].append(f"Spreadsheet not found. Check the Spreadsheet ID: {extracted_id}")
            else:
                results['errors'].append(f"Read access error: {error_str}")
            return Response(results, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Test write access
        try:
            ensure_header_row(sheets_config)
            results['info']['write_access'] = True
        except Exception as e:
            error_str = str(e)
            service_account_email = credentials_dict.get('client_email', 'N/A')
            
            if 'PERMISSION_DENIED' in error_str or '403' in error_str or 'does not have permission' in error_str.lower():
                results['errors'].append(
                    f"❌ Write Permission Denied: The service account does not have write access to the Google Sheet."
                )
                results['info']['service_account_email'] = service_account_email
                results['info']['fix_instructions'] = [
                    f"1. Open your Google Sheet: https://docs.google.com/spreadsheets/d/{extracted_id}/edit",
                    f"2. Click the 'Share' button (top right)",
                    f"3. Add this email address: {service_account_email}",
                    f"4. Give it 'Editor' access (not just Viewer)",
                    f"5. Click 'Send' or 'Done'",
                    f"6. Try testing the connection again"
                ]
            else:
                results['errors'].append(f"Write access error: {error_str}")
            return Response(results, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        results['success'] = True
        results['info']['message'] = "Google Sheets is properly configured and ready to use!"
        return Response(results)
        
    except Exception as e:
        results['errors'].append(f"Unexpected error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return Response(results, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
            files_deleted = []
            
            # Delete all associated media files
            if video.local_file:
                try:
                    video.local_file.delete(save=False)
                    files_deleted.append('local_file')
                except Exception:
                    pass
            
            if video.voice_removed_video:
                try:
                    video.voice_removed_video.delete(save=False)
                    files_deleted.append('voice_removed_video')
                except Exception:
                    pass
            
            if video.final_processed_video:
                try:
                    video.final_processed_video.delete(save=False)
                    files_deleted.append('final_processed_video')
                except Exception:
                    pass
            
            if video.synthesized_audio:
                try:
                    video.synthesized_audio.delete(save=False)
                    files_deleted.append('synthesized_audio')
                except Exception:
                    pass
            
            # Delete from Cloudinary if exists
            if upload_video_file and video.video_id:
                try:
                    from .cloudinary_service import get_cloudinary_config
                    import cloudinary.uploader
                    config = get_cloudinary_config()
                    if config:
                        cloudinary.config(
                            cloud_name=config['cloud_name'],
                            api_key=config['api_key'],
                            api_secret=config['api_secret']
                        )
                        public_id = f"videos/final/{video.video_id}"
                        cloudinary.uploader.destroy(public_id, resource_type='video')
                        files_deleted.append('cloudinary_video')
                except Exception:
                    pass
            
            # Delete from Google Sheets if synced
            if video.google_sheets_synced and add_video_to_sheet:
                try:
                    from .google_sheets_service import get_google_sheets_service
                    sheets_config = get_google_sheets_service()
                    if sheets_config:
                        service = sheets_config['service']
                        spreadsheet_id = sheets_config['spreadsheet_id']
                        sheet_name = sheets_config['sheet_name']
                        video_id = video.video_id or str(video.id)
                        
                        all_rows = service.spreadsheets().values().get(
                            spreadsheetId=spreadsheet_id,
                            range=f'{sheet_name}!A:J'
                        ).execute()
                        
                        if all_rows.get('values'):
                            for idx, row in enumerate(all_rows['values'], start=1):
                                if len(row) > 5 and row[5] == video_id:
                                    service.spreadsheets().batchUpdate(
                                        spreadsheetId=spreadsheet_id,
                                        body={
                                            'requests': [{
                                                'deleteDimension': {
                                                    'range': {
                                                        'sheetId': 0,
                                                        'dimension': 'ROWS',
                                                        'startIndex': idx,
                                                        'endIndex': idx + 1
                                                    }
                                                }
                                            }]
                                        }
                                    ).execute()
                                    files_deleted.append('google_sheets_row')
                                    break
                except Exception:
                    pass
            
            # Delete the video record
            video.delete()
            deleted_count += 1
            results.append({
                "id": video.id,
                "status": "deleted",
                "files_deleted": files_deleted
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

