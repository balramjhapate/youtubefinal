import os
import sys
from django.conf import settings
from django.core.files.base import ContentFile

# Check Python version first - neucodec requires Python 3.10+
PYTHON_VERSION_OK = sys.version_info >= (3, 10)
PYTHON_VERSION_ERROR = None
if not PYTHON_VERSION_OK:
    PYTHON_VERSION_ERROR = f"Python 3.10+ is required for voice synthesis. Current version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"Warning: {PYTHON_VERSION_ERROR}")

# Try to import required libraries
AUDIO_LIBS_AVAILABLE = False
AUDIO_LIBS_ERROR = None
if PYTHON_VERSION_OK:
    try:
        import torch
        import soundfile as sf
        import numpy as np
        AUDIO_LIBS_AVAILABLE = True
    except ImportError as e:
        AUDIO_LIBS_ERROR = str(e)
        print(f"Warning: Audio processing libraries not available: {e}")
else:
    AUDIO_LIBS_ERROR = PYTHON_VERSION_ERROR

# Add local neutts_air_lib to path
sys.path.append(os.path.join(settings.BASE_DIR, 'downloader', 'neutts_air_lib'))

NeuTTSAir = None
NEUTTS_ERROR = None

if PYTHON_VERSION_OK:
    try:
        from neuttsair.neutts import NeuTTSAir
    except ImportError as e:
        NEUTTS_ERROR = f"NeuTTS Air library not found: {e}"
        print(f"Warning: {NEUTTS_ERROR}")
    except Exception as e:
        NEUTTS_ERROR = f"Error loading NeuTTS Air: {e}"
        print(f"Warning: {NEUTTS_ERROR}")
else:
    NEUTTS_ERROR = PYTHON_VERSION_ERROR

class VoiceCloningService:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VoiceCloningService, cls).__new__(cls)
        return cls._instance

    def is_available(self):
        """Check if voice cloning service is available."""
        return NeuTTSAir is not None and AUDIO_LIBS_AVAILABLE

    def get_status(self):
        """Get detailed status of the voice cloning service."""
        # Check Python version first
        if not PYTHON_VERSION_OK:
            return {
                'available': False,
                'error': PYTHON_VERSION_ERROR,
                'model_loaded': False,
                'python_version_required': '3.10+',
                'python_version_current': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            }
        if not AUDIO_LIBS_AVAILABLE:
            return {
                'available': False,
                'error': AUDIO_LIBS_ERROR or 'Audio processing libraries (torch, soundfile, numpy) not installed',
                'model_loaded': False
            }
        if NeuTTSAir is None:
            return {
                'available': False,
                'error': NEUTTS_ERROR or 'NeuTTS Air library not available',
                'model_loaded': False
            }
        return {
            'available': True,
            'error': None,
            'model_loaded': self._model is not None
        }

    def load_model(self):
        """Load the NeuTTS Air model if not already loaded."""
        if not AUDIO_LIBS_AVAILABLE:
            raise RuntimeError("Audio processing libraries (torch, soundfile, numpy) not installed. Please install: pip install torch soundfile numpy")

        if NeuTTSAir is None:
            raise RuntimeError(NEUTTS_ERROR or "NeuTTS Air library not available. Please check the neutts_air_lib installation.")

        if self._model is None:
            try:
                print("Loading NeuTTS Air model...")
                self._model = NeuTTSAir(
                    backbone_repo="neuphonic/neutts-air",
                    backbone_device="cpu",  # Use CPU for compatibility
                    codec_repo="neuphonic/neucodec",
                    codec_device="cpu"
                )
                print("NeuTTS Air model loaded successfully.")
            except Exception as e:
                print(f"Failed to load NeuTTS Air model: {e}")
                raise RuntimeError(f"Failed to load NeuTTS Air model: {e}")

    def clone_voice(self, audio_path, text):
        """
        Generate reference codes for voice cloning.

        Args:
            audio_path (str): Path to reference audio file (.wav)
            text (str): Transcript of the reference audio

        Returns:
            torch.Tensor: Encoded reference codes
        """
        self.load_model()
        if not self._model:
            raise RuntimeError("Model not initialized")

        # Check audio duration and trim if too long
        # Max ~20 seconds to stay well under 2048 token limit (50 frames/sec * 20 = 1000 tokens)
        # This leaves room for text tokens and generation
        import librosa
        import tempfile

        wav, sr = librosa.load(audio_path, sr=16000, mono=True)
        duration = len(wav) / sr
        max_duration = 20.0  # seconds - keep short for best results

        if duration > max_duration:
            print(f"Reference audio is {duration:.1f}s, trimming to {max_duration}s to avoid token limit")
            # Trim to max_duration seconds
            max_samples = int(max_duration * sr)
            wav = wav[:max_samples]

            # Save trimmed audio to temp file
            temp_path = tempfile.mktemp(suffix='.wav')
            sf.write(temp_path, wav, sr)
            result = self._model.encode_reference(temp_path)
            os.remove(temp_path)
            return result

        return self._model.encode_reference(audio_path)

    def synthesize(self, text, voice_profile, output_path=None):
        """
        Synthesize speech using a voice profile.

        Args:
            text (str): Text to synthesize
            voice_profile (VoiceProfile): Voice profile to use
            output_path (str, optional): Path to save output file

        Returns:
            str: Path to generated audio file
        """
        self.load_model()
        if not self._model:
            raise RuntimeError("Model not initialized")

        # Load reference codes
        # In a real app, we might cache these codes. For now, re-encode.
        # Ideally, we should save the tensor to disk and load it.

        ref_audio_path = voice_profile.reference_audio.path

        # Ensure reference text is clean and truncated to avoid token limit
        # The model has a 2048 token limit, so we limit reference text to ~200 chars
        ref_text = voice_profile.reference_text.strip()
        if len(ref_text) > 200:
            ref_text = ref_text[:200]
            print(f"Reference text truncated to 200 characters to avoid token limit")

        # Also limit synthesis text to avoid token overflow
        if len(text) > 500:
            text = text[:500]
            print(f"Synthesis text truncated to 500 characters to avoid token limit")

        # Generate reference codes
        print(f"Encoding reference audio: {ref_audio_path}")
        ref_codes = self.clone_voice(ref_audio_path, ref_text)

        # Check if text contains non-ASCII (Hindi/Devanagari) characters
        # NeuTTS Air only supports English, so we need to transliterate Hindi to romanized form
        def contains_devanagari(s):
            return any('\u0900' <= c <= '\u097F' for c in s)

        if contains_devanagari(text):
            print(f"Detected Hindi text, transliterating to romanized form...")
            try:
                from indic_transliteration import sanscript
                from indic_transliteration.sanscript import transliterate
                text = transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
                # Clean up ITRANS output for better TTS
                text = text.replace('.a', 'a').replace('~N', 'n').replace('~n', 'n')
                print(f"Transliterated text: {text[:100]}...")
            except ImportError:
                print("Warning: indic_transliteration not installed, using basic transliteration")
                # Basic fallback - just use the text as-is (won't work well)
                pass

        # Generate audio
        print(f"Synthesizing text: {text[:50]}...")
        wav = self._model.infer(text, ref_codes, ref_text)

        # Save to file
        if output_path is None:
            filename = f"synth_{voice_profile.id}_{int(os.times()[4])}.wav"
            output_path = os.path.join(settings.MEDIA_ROOT, 'synthesized', filename)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

        sf.write(output_path, wav, 24000)
        return output_path

def get_voice_cloning_service():
    return VoiceCloningService()
