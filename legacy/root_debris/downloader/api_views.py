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
    perform_extraction, extract_video_id, translate_text,
    transcribe_video, download_file,
    process_video_with_ai
)


class VideoDownloadViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Video Downloads - handles all CRUD operations
    """
    queryset = VideoDownload.objects.all().order_by('-created_at')
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.action == 'list':
            return VideoDownloadListSerializer
        return VideoDownloadSerializer

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
        """Extract video from Xiaohongshu URL"""
        serializer = VideoExtractSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        url = serializer.validated_data['url']

        # Check for existing video by ID
        video_id = extract_video_id(url)
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
                        "cached": True
                    })
                else:
                    return Response({
                        "error": f"Video with ID '{video_id}' already exists but extraction failed."
                    }, status=status.HTTP_400_BAD_REQUEST)

        # Create pending download record
        try:
            download = VideoDownload.objects.create(
                url=url,
                video_id=video_id,
                status='pending'
            )
        except Exception as e:
            if 'video_id' in str(e) or 'UNIQUE constraint' in str(e):
                return Response({
                    "error": f"Video with ID '{video_id}' already exists."
                }, status=status.HTTP_400_BAD_REQUEST)
            raise

        # Perform extraction
        video_data = perform_extraction(url)

        if video_data:
            download.status = 'success'
            download.extraction_method = video_data.get('method', '')
            download.video_url = video_data.get('video_url', '')
            download.cover_url = video_data.get('cover_url', '')

            original_title = video_data.get('original_title', '')
            original_desc = video_data.get('original_description', '')

            download.original_title = original_title
            download.original_description = original_desc
            download.title = translate_text(original_title, target='en')
            download.description = translate_text(original_desc, target='en')
            download.save()

            return Response({
                "id": download.id,
                "video_url": download.video_url,
                "title": download.title,
                "cover_url": download.cover_url,
                "method": download.extraction_method,
                "cached": False
            }, status=status.HTTP_201_CREATED)
        else:
            download.status = 'failed'
            download.error_message = "Could not extract video. The link might be invalid or protected."
            download.save()

            return Response({
                "error": "Could not extract video. The link might be invalid or protected."
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
            file_content = download_file(video.video_url)
            if file_content:
                filename = f"{video.video_id or video.id}.mp4"
                video.local_file.save(filename, file_content)
                video.is_downloaded = True
                video.save()

                return Response({
                    "status": "success",
                    "file_url": request.build_absolute_uri(video.local_file.url)
                })
            else:
                return Response({
                    "error": "Failed to download video"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def transcribe(self, request, pk=None):
        """Start transcription for a video"""
        video = self.get_object()

        if video.transcription_status == 'transcribing':
            return Response({
                "status": "already_processing",
                "message": "Transcription is already in progress"
            })

        if video.transcription_status == 'transcribed':
            return Response({
                "status": "already_transcribed",
                "transcript": video.transcript,
                "transcript_hindi": video.transcript_hindi,
                "language": video.transcript_language
            })

        # Start transcription
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
                video.transcript_error_message = ''
                video.save()

                return Response({
                    "status": "success",
                    "transcript": video.transcript,
                    "transcript_hindi": video.transcript_hindi,
                    "language": video.transcript_language
                })
            else:
                video.transcription_status = 'failed'
                video.transcript_error_message = result.get('error', 'Unknown error')
                video.save()

                return Response({
                    "status": "failed",
                    "error": result.get('error', 'Unknown error')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            video.transcription_status = 'failed'
            video.transcript_error_message = str(e)
            video.save()

            return Response({
                "status": "failed",
                "error": str(e)
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


