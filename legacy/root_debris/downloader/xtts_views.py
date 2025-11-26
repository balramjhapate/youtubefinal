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
from .xtts_service import XTTSService
from .models import ClonedVoice
from .serializers import ClonedVoiceSerializer
import logging

logger = logging.getLogger(__name__)

class XTTSGenerateView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        text = request.data.get('text')
        language = request.data.get('language')
        reference_audio = request.FILES.get('reference_audio')
        voice_id = request.data.get('voice_id')
        
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

        except Exception as e:
            logger.error(f"XTTS Generation Error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class XTTSLanguagesView(APIView):
    def get(self, request, *args, **kwargs):
        service = XTTSService()
        return Response(service.get_languages(), status=status.HTTP_200_OK)

class ClonedVoiceViewSet(viewsets.ModelViewSet):
    queryset = ClonedVoice.objects.all().order_by('-created_at')
    serializer_class = ClonedVoiceSerializer
    parser_classes = (MultiPartParser, FormParser)
