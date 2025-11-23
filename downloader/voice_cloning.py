import os
import sys
import torch
import soundfile as sf
import numpy as np
from django.conf import settings
from django.core.files.base import ContentFile

# Add local neutts_air_lib to path
sys.path.append(os.path.join(settings.BASE_DIR, 'downloader', 'neutts_air_lib'))

try:
    from neuttsair.neutts import NeuTTSAir
except ImportError:
    NeuTTSAir = None
    print("Warning: neuttsair library not found or dependencies missing.")

class VoiceCloningService:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VoiceCloningService, cls).__new__(cls)
        return cls._instance

    def load_model(self):
        """Load the NeuTTS Air model if not already loaded."""
        if self._model is None and NeuTTSAir:
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
                raise

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
        
        # Ensure reference text is clean
        ref_text = voice_profile.reference_text.strip()
        
        # Generate reference codes
        print(f"Encoding reference audio: {ref_audio_path}")
        ref_codes = self.clone_voice(ref_audio_path, ref_text)
        
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
