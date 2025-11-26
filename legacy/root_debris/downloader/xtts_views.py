import os
import uuid
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework.views import APIView
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from .xtts_service import XTTSService, TTS_AVAILABLE
from .models import ClonedVoice
from .serializers import ClonedVoiceSerializer
import logging

logger = logging.getLogger(__name__)

class XTTSGenerateView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        # Check if TTS is available
        if not TTS_AVAILABLE:
            import sys
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
            return Response(
                {
                    'error': f'XTTS service is not available. TTS library requires Python 3.9-3.11 (NOT 3.12+). Current version is Python {python_version}. Please use Python 3.9, 3.10, or 3.11.'
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        text = request.data.get('text')
        language = request.data.get('language', '').strip()
        reference_audio = request.FILES.get('reference_audio')
        voice_id = request.data.get('voice_id')
        
        # Normalize language code - handle display names sent from frontend
        language_map = {
            'english': 'en', 'hindi': 'hi', 'spanish': 'es', 'french': 'fr',
            'german': 'de', 'italian': 'it', 'portuguese': 'pt', 'polish': 'pl',
            'turkish': 'tr', 'russian': 'ru', 'dutch': 'nl', 'czech': 'cs',
            'arabic': 'ar', 'chinese': 'zh-cn', 'japanese': 'ja', 'hungarian': 'hu',
            'korean': 'ko'
        }
        # Convert to lowercase for lookup
        language_lower = language.lower()
        if language_lower in language_map:
            language = language_map[language_lower]
            logger.info(f"Converted language '{request.data.get('language')}' to code '{language}'")
        
        # Advanced parameters
        speed = float(request.data.get('speed', 1.0))
        temperature = float(request.data.get('temperature', 0.75))
        repetition_penalty = float(request.data.get('repetition_penalty', 5.0))
        top_k = int(request.data.get('top_k', 50))
        top_p = float(request.data.get('top_p', 0.85))

        if not text or not language:
             return Response(
                {'error': 'Missing required fields: text, language'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not reference_audio and not voice_id:
            return Response(
                {'error': 'Either reference_audio or voice_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ref_path = None
        temp_ref_created = False

        try:
            if voice_id:
                try:
                    voice = ClonedVoice.objects.get(id=voice_id)
                    ref_path = voice.file.path
                except ClonedVoice.DoesNotExist:
                    return Response({'error': 'Voice not found'}, status=status.HTTP_404_NOT_FOUND)
            else:
                # Save reference audio temporarily
                ref_filename = f"ref_{uuid.uuid4()}.wav"
                ref_path = os.path.join(settings.MEDIA_ROOT, 'temp_references', ref_filename)
                os.makedirs(os.path.dirname(ref_path), exist_ok=True)
                
                with open(ref_path, 'wb+') as destination:
                    for chunk in reference_audio.chunks():
                        destination.write(chunk)
                temp_ref_created = True

            # Generate output path
            output_filename = f"generated_{uuid.uuid4()}.wav"
            output_rel_path = os.path.join('generated_audio', output_filename)
            output_path = os.path.join(settings.MEDIA_ROOT, output_rel_path)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Generate speech
            service = XTTSService()
            service.generate_speech(
                text=text, 
                speaker_wav_path=ref_path, 
                language=language, 
                output_path=output_path,
                speed=speed,
                temperature=temperature,
                repetition_penalty=repetition_penalty,
                top_k=top_k,
                top_p=top_p
            )

            # Clean up temporary reference audio
            if temp_ref_created and os.path.exists(ref_path):
                os.remove(ref_path)

            # Return URL
            audio_url = settings.MEDIA_URL + output_rel_path
            return Response({'audio_url': audio_url}, status=status.HTTP_200_OK)

        except ImportError as e:
            logger.error(f"XTTS Import Error: {str(e)}")
            import sys
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
            return Response(
                {
                    'error': f'XTTS service is not available. TTS library requires Python 3.9-3.11 (NOT 3.12+). Current version is Python {python_version}. Please use Python 3.9, 3.10, or 3.11.',
                    'details': str(e)
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"XTTS Generation Error: {str(e)}\n{error_traceback}")
            error_message = str(e)
            # Provide more user-friendly error messages
            if 'model' in error_message.lower() or 'load' in error_message.lower():
                error_message = f"Failed to load XTTS model: {error_message}"
            elif 'download' in error_message.lower() or 'downloading' in error_message.lower():
                error_message = f"Model is still downloading. Please wait a few minutes and try again. Error: {error_message}"
            return Response(
                {'error': error_message, 'details': error_traceback if settings.DEBUG else None},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class XTTSLanguagesView(APIView):
    def get(self, request, *args, **kwargs):
        # Languages are always available, even if TTS is not
        service = XTTSService()
        return Response(service.get_languages(), status=status.HTTP_200_OK)

class ClonedVoiceViewSet(viewsets.ModelViewSet):
    queryset = ClonedVoice.objects.all().order_by('-created_at')
    serializer_class = ClonedVoiceSerializer
    parser_classes = (MultiPartParser, FormParser)
    
    def get_serializer_context(self):
        """Add request to serializer context for building absolute URLs"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def list(self, request, *args, **kwargs):
        """List all cloned voices"""
        try:
            return super().list(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error listing voices: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Failed to list voices: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def create(self, request, *args, **kwargs):
        """Create a new cloned voice"""
        try:
            # Validate required fields
            if not request.data.get('name'):
                return Response(
                    {'error': 'Voice name is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if not request.FILES.get('file'):
                return Response(
                    {'error': 'Audio file is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return super().create(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error creating voice: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Failed to save voice: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """Delete a cloned voice"""
        try:
            return super().destroy(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error deleting voice: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Failed to delete voice: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
