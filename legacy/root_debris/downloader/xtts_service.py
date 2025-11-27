import os
import sys
import logging
from io import StringIO

logger = logging.getLogger(__name__)

# Set environment variable to auto-accept Coqui TTS license
os.environ['COQUI_TOS_AGREED'] = '1'

# Lazy import TTS to avoid blocking Django startup if TTS dependencies aren't compatible
try:
    import torch
    # Redirect stdin temporarily to avoid interactive prompts
    old_stdin = sys.stdin
    sys.stdin = StringIO('y\n')
    try:
        from TTS.api import TTS
        TTS_AVAILABLE = True
    finally:
        sys.stdin = old_stdin
except (ImportError, TypeError) as e:
    logger.warning(f"TTS library not available: {e}. XTTS features will be disabled.")
    TTS_AVAILABLE = False
    TTS = None
    torch = None

class XTTSService:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(XTTSService, cls).__new__(cls)
        return cls._instance

    @staticmethod
    def get_device():
        """
        Determine the best available device for PyTorch.
        Priority: MPS (Apple Silicon GPU) > CUDA (NVIDIA GPU) > CPU
        """
        if not TTS_AVAILABLE or torch is None:
            return "cpu"
        
        # Check for Apple Silicon GPU (MPS) - for Mac with M1/M2/M3/M4 chips
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"
        
        # Check for NVIDIA GPU (CUDA)
        if torch.cuda.is_available():
            return "cuda"
        
        # Fallback to CPU
        return "cpu"

    def load_model(self):
        if not TTS_AVAILABLE:
            raise ImportError("TTS library is not available. Please check your Python version (requires 3.9-3.11, NOT 3.12+) and ensure all dependencies are installed.")
        if self._model is None:
            try:
                device = self.get_device()
                device_name = {
                    "mps": "Apple Silicon GPU (MPS)",
                    "cuda": "NVIDIA GPU (CUDA)",
                    "cpu": "CPU"
                }.get(device, device)
                logger.info(f"Loading XTTS v2 model on {device_name} ({device})...")
                # Redirect stdin to auto-accept license prompt
                old_stdin = sys.stdin
                sys.stdin = StringIO('y\n')
                try:
                    # This will download the model on first run
                    self._model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
                    logger.info(f"XTTS v2 model loaded successfully on {device_name}.")
                finally:
                    sys.stdin = old_stdin
            except Exception as e:
                logger.error(f"Failed to load XTTS model: {str(e)}")
                raise e
        return self._model

    def generate_speech(self, text, speaker_wav_path, language, output_path, 
                        speed=1.0, temperature=0.75, repetition_penalty=5.0, top_k=50, top_p=0.85):
        """
        Generate speech using XTTS v2 with advanced parameters.
        """
        model = self.load_model()
        
        try:
            logger.info(f"Generating speech for text: {text[:50]}... in {language}")
            model.tts_to_file(
                text=text,
                speaker_wav=speaker_wav_path,
                language=language,
                file_path=output_path,
                speed=speed,
                temperature=temperature,
                repetition_penalty=repetition_penalty,
                top_k=top_k,
                top_p=top_p
            )
            return output_path
        except Exception as e:
            logger.error(f"Error generating speech: {str(e)}")
            raise e

    def get_languages(self):
        return {
            "English": "en",
            "Hindi": "hi",
            "Spanish": "es",
            "French": "fr",
            "German": "de",
            "Italian": "it",
            "Portuguese": "pt",
            "Polish": "pl",
            "Turkish": "tr",
            "Russian": "ru",
            "Dutch": "nl",
            "Czech": "cs",
            "Arabic": "ar",
            "Chinese": "zh-cn",
            "Japanese": "ja",
            "Hungarian": "hu",
            "Korean": "ko",
        }
