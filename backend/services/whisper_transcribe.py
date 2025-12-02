"""
Whisper-based Audio Transcription Module

This module provides high-quality audio transcription using OpenAI Whisper with:
- Automatic language detection
- Time-aligned segments with timestamps
- Confidence checking and retry logic for low-confidence segments
- Optional WhisperX support for improved alignment and speaker diarization

Author: Generated for RedNote Video Processing System
Date: 2025-11-27
"""

import os
import whisper
from typing import List, Dict, Optional, Tuple
from django.conf import settings


# Global model cache to avoid reloading models
_MODEL_CACHE = {}


def load_whisper_model(model_name: str = "medium"):
    """
    Load Whisper model once and cache it for reuse.
    Optimized for Mac Mini M4 (16GB RAM) - default: 'medium' for best accuracy/performance balance.
    
    Args:
        model_name: Whisper model size ('tiny', 'base', 'small', 'medium', 'large') - Default: 'medium'
                   - tiny: Fastest, least accurate (~1GB RAM)
                   - base: Good balance (~1GB RAM)
                   - small: Better accuracy (~2GB RAM)
                   - medium: High accuracy (~5GB RAM) - RECOMMENDED for Mac Mini M4 (16GB RAM)
                   - large: Best accuracy (~10GB RAM) - May be slow on 16GB systems
    
    Returns:
        Loaded Whisper model instance
    
    Raises:
        Exception: If model fails to load
    """
    global _MODEL_CACHE
    
    if model_name in _MODEL_CACHE:
        print(f"Using cached Whisper model: {model_name}")
        return _MODEL_CACHE[model_name]
    
    try:
        print(f"Loading Whisper model: {model_name} (this may take a moment on first load)...")
        model = whisper.load_model(model_name)
        _MODEL_CACHE[model_name] = model
        print(f"Whisper model '{model_name}' loaded successfully")
        return model
    except Exception as e:
        print(f"ERROR: Failed to load Whisper model '{model_name}': {e}")
        raise


def transcribe_with_whisper(
    model,
    audio_path: str,
    task: str = "transcribe",
    language: Optional[str] = None
) -> Dict:
    """
    Transcribe audio and auto-detect language with time-aligned segments.
    
    Args:
        model: Loaded Whisper model instance
        audio_path: Path to audio file
        task: 'transcribe' (keep original language) or 'translate' (translate to English)
        language: Optional language code to force (e.g., 'en', 'hi', 'zh'). 
                 If None, auto-detect language.
    
    Returns:
        dict: {
            'language': str (ISO language code, e.g., 'en', 'hi', 'zh'),
            'text': str (full transcript text),
            'segments': List[{
                'start': float (start time in seconds),
                'end': float (end time in seconds),
                'text': str (segment text),
                'confidence': float (avg_logprob, negative value, closer to 0 = higher confidence)
            }],
            'status': 'success' or 'failed',
            'error': str or None
        }
    
    Example:
        >>> model = load_whisper_model('base')
        >>> result = transcribe_with_whisper(model, 'audio.wav')
        >>> print(f"Language: {result['language']}")
        >>> print(f"Text: {result['text']}")
        >>> for seg in result['segments']:
        ...     print(f"{seg['start']:.2f}s - {seg['end']:.2f}s: {seg['text']}")
    """
    try:
        if not os.path.exists(audio_path):
            return {
                'language': None,
                'text': '',
                'segments': [],
                'status': 'failed',
                'error': f'Audio file not found: {audio_path}'
            }
        
        # Prepare transcription options
        options = {'task': task, 'verbose': False}
        if language:
            options['language'] = language
        
        print(f"Transcribing audio: {audio_path}")
        print(f"Options: task={task}, language={language or 'auto-detect'}")
        
        # Transcribe
        result = model.transcribe(audio_path, **options)
        
        # Extract language (auto-detected or specified)
        detected_language = result.get('language') or result.get('lang') or language or 'unknown'
        
        # Extract full text
        full_text = result.get('text', '').strip()
        
        # Process segments with timestamps and confidence
        segments = []
        for seg in result.get('segments', []):
            segments.append({
                'start': float(seg.get('start', 0)),
                'end': float(seg.get('end', 0)),
                'text': seg.get('text', '').strip(),
                'confidence': float(seg.get('avg_logprob', 0.0))  # Negative value, closer to 0 = better
            })
        
        print(f"Transcription complete: Language={detected_language}, "
              f"Text length={len(full_text)} chars, Segments={len(segments)}")
        
        return {
            'language': detected_language,
            'text': full_text,
            'segments': segments,
            'status': 'success',
            'error': None
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"ERROR in transcribe_with_whisper: {error_msg}")
        return {
            'language': None,
            'text': '',
            'segments': [],
            'status': 'failed',
            'error': error_msg
        }


def check_segment_confidence(segments: List[Dict], threshold: float = -1.5) -> Tuple[List[Dict], List[Dict]]:
    """
    Check segment confidence scores and identify low-confidence segments.
    
    Args:
        segments: List of segment dicts with 'confidence' field (avg_logprob)
        threshold: Confidence threshold (default: -1.5). 
                  Segments with confidence < threshold are considered low-confidence.
                  Note: avg_logprob is negative, so -1.5 means values like -2.0, -3.0 are low confidence.
    
    Returns:
        Tuple of (high_confidence_segments, low_confidence_segments)
    
    Example:
        >>> high, low = check_segment_confidence(segments, threshold=-1.5)
        >>> print(f"High confidence: {len(high)}, Low confidence: {len(low)}")
    """
    high_confidence = []
    low_confidence = []
    
    for seg in segments:
        confidence = seg.get('confidence', 0.0)
        if confidence < threshold:
            low_confidence.append(seg)
        else:
            high_confidence.append(seg)
    
    return high_confidence, low_confidence


def retry_low_confidence_segments(
    audio_path: str,
    segments: List[Dict],
    current_model_name: str,
    threshold: float = -1.5
) -> Dict:
    """
    Retry transcription of low-confidence segments with a larger model.
    
    Args:
        audio_path: Path to audio file
        segments: List of segments from initial transcription
        current_model_name: Current model size used
        threshold: Confidence threshold for retry
    
    Returns:
        dict: {
            'improved': bool (whether retry improved results),
            'segments': List[Dict] (updated segments),
            'retry_count': int (number of segments retried),
            'status': 'success' or 'failed',
            'error': str or None
        }
    """
    try:
        # Check for low-confidence segments
        high_conf, low_conf = check_segment_confidence(segments, threshold)
        
        if not low_conf:
            print("All segments have acceptable confidence. No retry needed.")
            return {
                'improved': False,
                'segments': segments,
                'retry_count': 0,
                'status': 'success',
                'error': None
            }
        
        print(f"Found {len(low_conf)} low-confidence segments (threshold: {threshold})")
        
        # Determine larger model to use
        model_hierarchy = ['tiny', 'base', 'small', 'medium', 'large']
        try:
            current_idx = model_hierarchy.index(current_model_name)
            if current_idx >= len(model_hierarchy) - 1:
                print(f"Already using largest model ({current_model_name}). Cannot retry with larger model.")
                return {
                    'improved': False,
                    'segments': segments,
                    'retry_count': 0,
                    'status': 'success',
                    'error': 'Already using largest model'
                }
            larger_model_name = model_hierarchy[current_idx + 1]
        except ValueError:
            print(f"Unknown model name: {current_model_name}. Cannot determine larger model.")
            return {
                'improved': False,
                'segments': segments,
                'retry_count': 0,
                'status': 'failed',
                'error': f'Unknown model name: {current_model_name}'
            }
        
        print(f"Retrying with larger model: {larger_model_name}")
        
        # Load larger model
        larger_model = load_whisper_model(larger_model_name)
        
        # Re-transcribe entire audio with larger model
        # (In production, you could extract and transcribe only low-confidence segments,
        #  but for simplicity, we re-transcribe the whole file)
        retry_result = transcribe_with_whisper(larger_model, audio_path)
        
        if retry_result['status'] == 'success':
            print(f"Retry successful with {larger_model_name}. "
                  f"New segments: {len(retry_result['segments'])}")
            return {
                'improved': True,
                'segments': retry_result['segments'],
                'retry_count': len(low_conf),
                'status': 'success',
                'error': None
            }
        else:
            print(f"Retry failed: {retry_result.get('error')}")
            return {
                'improved': False,
                'segments': segments,
                'retry_count': 0,
                'status': 'failed',
                'error': retry_result.get('error')
            }
            
    except Exception as e:
        error_msg = str(e)
        print(f"ERROR in retry_low_confidence_segments: {error_msg}")
        return {
            'improved': False,
            'segments': segments,
            'retry_count': 0,
            'status': 'failed',
            'error': error_msg
        }


def transcribe_with_whisperx(
    model_name: str,
    audio_path: str,
    device: str = "cpu",
    language: Optional[str] = None
) -> Dict:
    """
    Transcribe using WhisperX for improved timestamp alignment and optional speaker diarization.
    
    NOTE: This requires whisperx to be installed:
          pip install git+https://github.com/m-bain/whisperx.git
    
    Args:
        model_name: Whisper model size
        audio_path: Path to audio file
        device: 'cpu' or 'cuda'
        language: Optional language code
    
    Returns:
        dict: Similar to transcribe_with_whisper, but with improved timestamps
              and optional 'diarization' field with speaker labels
    """
    try:
        import whisperx
    except ImportError:
        return {
            'language': None,
            'text': '',
            'segments': [],
            'status': 'failed',
            'error': 'WhisperX not installed. Install with: pip install git+https://github.com/m-bain/whisperx.git'
        }
    
    try:
        print(f"Loading WhisperX model: {model_name} on {device}")
        model = whisperx.load_model(model_name, device=device)
        
        print(f"Transcribing with WhisperX: {audio_path}")
        result = model.transcribe(audio_path)
        
        detected_language = result.get('language', language or 'unknown')
        
        # Align with acoustic model for better timestamps
        print(f"Aligning timestamps for language: {detected_language}")
        model_a, metadata = whisperx.load_align_model(language_code=detected_language, device=device)
        result_aligned = whisperx.align(result['segments'], model_a, metadata, audio_path, device)
        
        # Optional: Speaker diarization
        diarization = None
        try:
            print("Attempting speaker diarization...")
            diarize_segments = whisperx.diarize(audio_path, device=device)
            diarization = diarize_segments
            print(f"Diarization complete: {len(diarize_segments) if diarize_segments else 0} speaker segments")
        except Exception as e:
            print(f"Diarization skipped or failed: {e}")
        
        # Format segments
        segments = []
        for seg in result_aligned.get('segments', []):
            segments.append({
                'start': float(seg.get('start', 0)),
                'end': float(seg.get('end', 0)),
                'text': seg.get('text', '').strip(),
                'confidence': float(seg.get('score', 0.0))  # WhisperX uses 'score' instead of 'avg_logprob'
            })
        
        full_text = ' '.join([seg['text'] for seg in segments])
        
        print(f"WhisperX transcription complete: Language={detected_language}, "
              f"Segments={len(segments)}")
        
        return {
            'language': detected_language,
            'text': full_text,
            'segments': segments,
            'diarization': diarization,
            'status': 'success',
            'error': None
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"ERROR in transcribe_with_whisperx: {error_msg}")
        return {
            'language': None,
            'text': '',
            'segments': [],
            'status': 'failed',
            'error': error_msg
        }


def format_segments_to_timestamped_text(segments: List[Dict]) -> str:
    """
    Convert segments to timestamped text format (HH:MM:SS text).
    
    Args:
        segments: List of segment dicts with 'start' and 'text'
    
    Returns:
        str: Formatted text with timestamps, e.g.:
             00:00:05 Hello world
             00:00:10 This is a test
    """
    lines = []
    for seg in segments:
        start = seg.get('start', 0)
        text = seg.get('text', '').strip()
        if text:
            hours = int(start // 3600)
            minutes = int((start % 3600) // 60)
            seconds = int(start % 60)
            timestamp = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            lines.append(f"{timestamp} {text}")
    return '\n'.join(lines)


def format_segments_to_plain_text(segments: List[Dict]) -> str:
    """
    Convert segments to plain text (no timestamps).
    
    Args:
        segments: List of segment dicts with 'text'
    
    Returns:
        str: Plain text without timestamps
    """
    return ' '.join([seg.get('text', '').strip() for seg in segments if seg.get('text', '').strip()])


def write_srt(segments: List[Dict], output_path: str) -> Optional[str]:
    """
    Write segments to SRT subtitle file format.
    
    Args:
        segments: List of segment dicts with 'start', 'end', 'text'
        output_path: Path to save SRT file
    
    Returns:
        str: Path to saved SRT file, or None if failed
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, seg in enumerate(segments, 1):
                start = seg.get('start', 0)
                end = seg.get('end', 0)
                text = seg.get('text', '').strip()
                
                if not text:
                    continue
                
                # Convert to SRT timestamp format (HH:MM:SS,mmm)
                start_h = int(start // 3600)
                start_m = int((start % 3600) // 60)
                start_s = int(start % 60)
                start_ms = int((start % 1) * 1000)
                
                end_h = int(end // 3600)
                end_m = int((end % 3600) // 60)
                end_s = int(end % 60)
                end_ms = int((end % 1) * 1000)
                
                f.write(f"{i}\n")
                f.write(f"{start_h:02d}:{start_m:02d}:{start_s:02d},{start_ms:03d} --> "
                       f"{end_h:02d}:{end_m:02d}:{end_s:02d},{end_ms:03d}\n")
                f.write(f"{text}\n\n")
        
        print(f"SRT file saved: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"ERROR writing SRT file: {e}")
        return None
