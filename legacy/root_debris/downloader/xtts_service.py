import os
import torch
from TTS.api import TTS
import logging

logger = logging.getLogger(__name__)

class XTTSService:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(XTTSService, cls).__new__(cls)
        return cls._instance

    def load_model(self):
        if self._model is None:
            try:
                device = "cuda" if torch.cuda.is_available() else "cpu"
                logger.info(f"Loading XTTS v2 model on {device}...")
                # This will download the model on first run
                self._model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
                logger.info("XTTS v2 model loaded successfully.")
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
