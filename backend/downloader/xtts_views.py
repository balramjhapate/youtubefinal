import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import SavedVoice

# TTS model - lazy loaded to avoid startup crashes
tts_model = None
TTS_AVAILABLE = False

# Check if TTS is available
try:
    import torch
    from TTS.api import TTS
    TTS_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: TTS library not available: {e}")
    print("Voice cloning features will be disabled. To enable, run: pip install TTS torch torchaudio")

def get_tts_model():
    global tts_model
    
    if not TTS_AVAILABLE:
        raise Exception("TTS library not installed. Please run: pip install TTS torch torchaudio")
    
    if tts_model is None:
        try:
            import torch
            from TTS.api import TTS
            # Use CUDA if available
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Loading XTTS model on {device}...")
            tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
            print("XTTS model loaded successfully")
        except Exception as e:
            print(f"Error loading XTTS model: {e}")
            raise Exception(f"XTTS model not available: {str(e)}")
    return tts_model

@csrf_exempt
@require_http_methods(["GET"])
def get_languages(request):
    """Get supported languages for XTTS"""
    # XTTS v2 supported languages
    languages = {
        "en": "English",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "it": "Italian",
        "pt": "Portuguese",
        "pl": "Polish",
        "tr": "Turkish",
        "ru": "Russian",
        "nl": "Dutch",
        "cs": "Czech",
        "ar": "Arabic",
        "zh-cn": "Chinese",
        "ja": "Japanese",
        "hu": "Hungarian",
        "ko": "Korean",
        "hi": "Hindi"
    }
    return JsonResponse(languages)

@csrf_exempt
@require_http_methods(["GET", "POST"])
def manage_voices(request):
    """Get all saved voices or save a new voice"""
    if request.method == "GET":
        voices = SavedVoice.objects.all().order_by('-created_at')
        data = []
        for voice in voices:
            data.append({
                "id": voice.id,
                "name": voice.name,
                "file": request.build_absolute_uri(voice.file.url),
                "created_at": voice.created_at.isoformat()
            })
        return JsonResponse(data, safe=False)
    
    elif request.method == "POST":
        try:
            name = request.POST.get('name')
            file = request.FILES.get('file')
            
            if not name or not file:
                return JsonResponse({"error": "Name and file are required"}, status=400)
            
            voice = SavedVoice.objects.create(name=name, file=file)
            
            return JsonResponse({
                "id": voice.id,
                "name": voice.name,
                "file": request.build_absolute_uri(voice.file.url),
                "created_at": voice.created_at.isoformat()
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_voice(request, voice_id):
    """Delete a saved voice"""
    try:
        voice = SavedVoice.objects.get(id=voice_id)
        voice.delete()
        return JsonResponse({"status": "success"})
    except SavedVoice.DoesNotExist:
        return JsonResponse({"error": "Voice not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def generate_speech(request):
    """Generate speech using XTTS"""
    try:
        # Handle both form data and JSON
        if request.content_type == 'application/json':
            data = json.loads(request.body.decode('utf-8'))
            text = data.get('text')
            language = data.get('language')
            voice_id = data.get('voice_id')
            reference_audio = None
            speed = float(data.get('speed', 1.0))
            temperature = float(data.get('temperature', 0.75))
            repetition_penalty = float(data.get('repetition_penalty', 2.0))
            top_k = int(data.get('top_k', 50))
            top_p = float(data.get('top_p', 0.85))
        else:
            text = request.POST.get('text')
            language = request.POST.get('language')
            voice_id = request.POST.get('voice_id')
            reference_audio = request.FILES.get('reference_audio')
            speed = float(request.POST.get('speed', 1.0))
            temperature = float(request.POST.get('temperature', 0.75))
            repetition_penalty = float(request.POST.get('repetition_penalty', 2.0))
            top_k = int(request.POST.get('top_k', 50))
            top_p = float(request.POST.get('top_p', 0.85))
        
        if not text or not language:
            return JsonResponse({"error": "Text and language are required"}, status=400)
        
        print(f"Generating speech: text='{text[:50]}...', language={language}, voice_id={voice_id}")
        
        # Diagnostic logging
        try:
            current_model = get_tts_model()
            print(f"DEBUG DIAGNOSTICS:")
            print(f"  - Model Device: {current_model.device}")
            print(f"  - Request Language: {language}")
            print(f"  - Settings: speed={speed}, temp={temperature}, rep_pen={repetition_penalty}")
        except Exception as diag_err:
            print(f"  - Diagnostic Error: {diag_err}")
        
        speaker_wav = None
        temp_speaker_file = None
        
        # Handle speaker audio
        if voice_id:
            try:
                voice = SavedVoice.objects.get(id=voice_id)
                speaker_wav = voice.file.path
                print(f"Using saved voice: {voice.name}")
            except SavedVoice.DoesNotExist:
                return JsonResponse({"error": "Voice not found"}, status=404)
        elif reference_audio:
            # Save temporary file
            import tempfile
            temp_dir = tempfile.gettempdir()
            temp_speaker_file = os.path.join(temp_dir, f"temp_speaker_{reference_audio.name}")
            with open(temp_speaker_file, 'wb+') as destination:
                for chunk in reference_audio.chunks():
                    destination.write(chunk)
            speaker_wav = temp_speaker_file
            print(f"Using uploaded reference audio")
        else:
            return JsonResponse({"error": "Either voice_id or reference_audio is required"}, status=400)
            
        # Log speaker file details
        if speaker_wav and os.path.exists(speaker_wav):
            try:
                file_size = os.path.getsize(speaker_wav)
                print(f"  - Speaker File: {speaker_wav}")
                print(f"  - File Size: {file_size} bytes")
                if file_size < 10000:  # Warning for very small files (< ~10KB)
                    print(f"  - WARNING: Speaker file seems very small!")
            except Exception as e:
                print(f"  - Error checking speaker file: {e}")
            
        # Generate audio
        try:
            model = get_tts_model()
        except Exception as e:
            error_msg = str(e)
            print(f"Failed to load TTS model: {error_msg}")
            return JsonResponse({
                "error": f"TTS model not available. Please ensure XTTS is installed: {error_msg}"
            }, status=500)
        
        output_filename = f"generated_{os.urandom(4).hex()}.wav"
        output_path = os.path.join(settings.MEDIA_ROOT, "generated_audio", output_filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        print(f"Generating audio to: {output_path}")
        
        model.tts_to_file(
            text=text,
            speaker_wav=speaker_wav,
            language=language,
            file_path=output_path,
            speed=speed,
            temperature=temperature,
            repetition_penalty=repetition_penalty,
            top_k=top_k,
            top_p=top_p
        )
        
        print(f"Audio generated successfully: {output_filename}")
        
        # Cleanup temp file
        if temp_speaker_file and os.path.exists(temp_speaker_file):
            os.remove(temp_speaker_file)
            
        audio_url = f"{settings.MEDIA_URL}generated_audio/{output_filename}"
        return JsonResponse({"audio_url": request.build_absolute_uri(audio_url)})
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error generating speech: {str(e)}")
        print(error_trace)
        return JsonResponse({"error": f"Speech generation failed: {str(e)}"}, status=500)
