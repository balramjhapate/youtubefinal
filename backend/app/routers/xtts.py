"""
XTTS (Text-to-Speech) endpoints router
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path

from app.models import get_db, SavedVoice
from app.schemas import (
    XTTSLanguageResponse, XTTSVoiceResponse,
    XTTSGenerateRequest, XTTSGenerateResponse
)

router = APIRouter(prefix="/xtts", tags=["XTTS"])

# TTS model - lazy loaded
tts_model = None
TTS_AVAILABLE = False

# Check if TTS is available
try:
    import torch
    from TTS.api import TTS
    TTS_AVAILABLE = True
except ImportError:
    print("WARNING: TTS library not available. Voice cloning features will be disabled.")


def get_tts_model():
    """Get or load TTS model"""
    global tts_model
    
    if not TTS_AVAILABLE:
        raise Exception("TTS library not installed. Please run: pip install TTS torch torchaudio")
    
    if tts_model is None:
        import torch
        from TTS.api import TTS
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading XTTS model on {device}...")
        tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
        print("XTTS model loaded successfully")
    
    return tts_model


@router.get("/languages/", response_model=dict)
async def get_languages():
    """
    Get supported languages for XTTS
    
    Returns a dictionary of language codes and their names
    """
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
    return languages


@router.get("/voices/", response_model=List[XTTSVoiceResponse])
async def list_voices(db: Session = Depends(get_db)):
    """
    Get all saved voices
    
    Returns a list of all saved voice profiles
    """
    voices = db.query(SavedVoice).order_by(SavedVoice.created_at.desc()).all()
    return voices


@router.post("/voices/", response_model=XTTSVoiceResponse)
async def create_voice(
    name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Save a new voice profile
    
    - **name**: Name for the voice
    - **file**: Audio file for voice cloning
    """
    if not name or not file:
        raise HTTPException(status_code=400, detail="Name and file are required")
    
    # Save file
    media_dir = Path("media/voices")
    media_dir.mkdir(parents=True, exist_ok=True)
    file_path = media_dir / f"{name}_{file.filename}"
    
    with open(file_path, 'wb') as f:
        content = await file.read()
        f.write(content)
    
    # Create database record
    voice = SavedVoice(
        name=name,
        file=str(file_path)
    )
    db.add(voice)
    db.commit()
    db.refresh(voice)
    
    return voice


@router.delete("/voices/{voice_id}/")
async def delete_voice(voice_id: int, db: Session = Depends(get_db)):
    """Delete a voice profile"""
    voice = db.query(SavedVoice).filter(SavedVoice.id == voice_id).first()
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
    
    # Delete file
    if voice.file:
        file_path = Path(voice.file)
        if file_path.exists():
            file_path.unlink()
    
    db.delete(voice)
    db.commit()
    
    return {"status": "success", "message": "Voice deleted"}


@router.post("/generate/", response_model=XTTSGenerateResponse)
async def generate_speech(
    text: str = Form(...),
    language: str = Form(...),
    voice_id: int = Form(None),
    db: Session = Depends(get_db)
):
    """
    Generate speech using XTTS
    
    - **text**: Text to synthesize
    - **language**: Language code (en, hi, es, etc.)
    - **voice_id**: Optional voice ID to use (if not provided, uses default)
    """
    if not TTS_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="XTTS service is not available. TTS library requires Python 3.9-3.11. Please install: pip install TTS torch torchaudio"
        )
    
    # Normalize language code
    language_map = {
        'english': 'en', 'hindi': 'hi', 'spanish': 'es', 'french': 'fr',
        'german': 'de', 'italian': 'it', 'portuguese': 'pt', 'polish': 'pl',
        'turkish': 'tr', 'russian': 'ru', 'dutch': 'nl', 'czech': 'cs',
        'arabic': 'ar', 'chinese': 'zh-cn', 'japanese': 'ja', 'hungarian': 'hu',
        'korean': 'ko'
    }
    language_lower = language.lower()
    if language_lower in language_map:
        language = language_map[language_lower]
    
    try:
        model = get_tts_model()
        
        # Get voice file if voice_id provided
        speaker_wav = None
        if voice_id:
            voice = db.query(SavedVoice).filter(SavedVoice.id == voice_id).first()
            if voice and voice.file:
                file_path = Path(voice.file)
                if file_path.exists():
                    speaker_wav = str(file_path)
        
        # Generate audio
        output_dir = Path("media/synthesized_audio")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"xtts_{voice_id or 'default'}_{hash(text)}.wav"
        
        if speaker_wav:
            model.tts_to_file(
                text=text,
                speaker_wav=speaker_wav,
                language=language,
                file_path=str(output_path)
            )
        else:
            # Use default voice
            model.tts_to_file(
                text=text,
                language=language,
                file_path=str(output_path)
            )
        
        if output_path.exists():
            audio_url = f"/media/synthesized_audio/{output_path.name}"
            return XTTSGenerateResponse(
                status="success",
                audio_url=audio_url,
                message="Speech generated successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Audio file was not created")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")

