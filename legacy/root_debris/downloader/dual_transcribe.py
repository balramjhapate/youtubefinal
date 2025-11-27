"""
Dual Transcription Function - Run both NCA and Whisper for comparison

This module provides a function to run both NCA and Whisper transcription
simultaneously and store results in separate database fields for comparison.
"""

from django.utils import timezone
from django.conf import settings
from . import whisper_transcribe
from .nca_toolkit_client import get_nca_client
from .utils import extract_audio_from_video, translate_text
import os


def transcribe_video_dual(video_download):
    """
    Run BOTH NCA and Whisper transcription for comparison.
    Stores results in separate database fields.
    
    Args:
        video_download: VideoDownload model instance
    
    Returns:
        dict: {
            'nca_result': dict (NCA transcription result),
            'whisper_result': dict (Whisper transcription result),
            'status': 'success' or 'partial' or 'failed'
        }
    """
    results = {
        'nca_result': None,
        'whisper_result': None,
        'status': 'failed'
    }
    
    # ========== NCA TRANSCRIPTION ==========
    print("\n" + "="*60)
    print("STARTING NCA TRANSCRIPTION")
    print("="*60)
    
    if getattr(settings, 'NCA_API_ENABLED', False):
        nca_client = get_nca_client()
        if nca_client:
            try:
                video_download.transcription_status = 'transcribing'
                video_download.transcript_started_at = timezone.now()
                video_download.save()
                
                print("Attempting NCA transcription...")
                
                # Try with video URL first
                if video_download.video_url:
                    nca_result = nca_client.transcribe_video(video_url=video_download.video_url)
                elif video_download.is_downloaded and video_download.local_file:
                    video_path = video_download.local_file.path
                    if os.path.exists(video_path):
                        nca_result = nca_client.transcribe_video(video_file_path=video_path)
                    else:
                        nca_result = {'status': 'failed', 'error': 'Video file not found'}
                else:
                    nca_result = {'status': 'failed', 'error': 'No video URL or file available'}
                
                if nca_result['status'] == 'success':
                    # Process and store NCA results
                    transcript_text = nca_result.get('text', '')
                    
                    # Format timestamps
                    segments = nca_result.get('segments', [])
                    if segments:
                        timestamped_lines = []
                        plain_lines = []
                        for seg in segments:
                            start = seg.get('start', 0)
                            text = seg.get('text', '').strip()
                            if text:
                                hours = int(start // 3600)
                                minutes = int((start % 3600) // 60)
                                seconds = int(start % 60)
                                timestamp = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                                timestamped_lines.append(f"{timestamp} {text}")
                                plain_lines.append(text)
                        
                        video_download.transcript = '\n'.join(timestamped_lines)
                        video_download.transcript_without_timestamps = ' '.join(plain_lines)
                    else:
                        video_download.transcript = transcript_text
                        video_download.transcript_without_timestamps = transcript_text
                    
                    # Translate to Hindi
                    if transcript_text:
                        print("Translating NCA transcript to Hindi...")
                        hindi_translation = translate_text(transcript_text, target='hi')
                        video_download.transcript_hindi = hindi_translation
                    
                    video_download.transcript_language = nca_result.get('language', 'unknown')
                    video_download.transcription_status = 'transcribed'
                    video_download.transcript_processed_at = timezone.now()
                    video_download.save()
                    
                    results['nca_result'] = nca_result
                    print(f"✓ NCA transcription successful: {len(transcript_text)} chars")
                else:
                    video_download.transcription_status = 'failed'
                    video_download.transcript_error_message = nca_result.get('error', 'Unknown error')
                    video_download.save()
                    print(f"✗ NCA transcription failed: {nca_result.get('error')}")
                    
            except Exception as e:
                print(f"✗ NCA transcription error: {e}")
                video_download.transcription_status = 'failed'
                video_download.transcript_error_message = str(e)
                video_download.save()
    else:
        print("NCA API disabled, skipping NCA transcription")
    
    # ========== WHISPER TRANSCRIPTION ==========
    print("\n" + "="*60)
    print("STARTING WHISPER TRANSCRIPTION")
    print("="*60)
    
    try:
        video_download.whisper_transcription_status = 'transcribing'
        video_download.whisper_transcript_started_at = timezone.now()
        video_download.save()
        
        # Ensure video is downloaded
        if not video_download.is_downloaded or not video_download.local_file:
            if video_download.video_url:
                print("Video not downloaded, downloading first...")
                from .utils import download_file
                file_content = download_file(video_download.video_url)
                if file_content:
                    filename = f"{video_download.video_id or 'video'}_{video_download.pk}.mp4"
                    video_download.local_file.save(filename, file_content, save=True)
                    video_download.is_downloaded = True
                    video_download.save()
                else:
                    raise Exception("Could not download video for Whisper transcription")
            else:
                raise Exception("No video file or URL available for Whisper transcription")
        
        video_path = video_download.local_file.path
        
        if not os.path.exists(video_path):
            raise Exception(f"Video file not found: {video_path}")
        
        # Extract audio
        print(f"Extracting audio from: {video_path}")
        audio_path = extract_audio_from_video(video_path)
        
        if not audio_path:
            raise Exception("Failed to extract audio from video")
        
        try:
            # Get Whisper configuration
            model_size = getattr(settings, 'WHISPER_MODEL_SIZE', 'base')
            confidence_threshold = getattr(settings, 'WHISPER_CONFIDENCE_THRESHOLD', -1.5)
            retry_enabled = getattr(settings, 'WHISPER_RETRY_WITH_LARGER_MODEL', True)
            
            print(f"Transcribing with Whisper (model: {model_size})...")
            
            # Load model and transcribe
            model = whisper_transcribe.load_whisper_model(model_size)
            whisper_result = whisper_transcribe.transcribe_with_whisper(
                model=model,
                audio_path=audio_path,
                task='transcribe',
                language=None  # Auto-detect
            )
            
            if whisper_result['status'] == 'success':
                # Check confidence and retry if needed
                if retry_enabled and whisper_result.get('segments'):
                    high_conf, low_conf = whisper_transcribe.check_segment_confidence(
                        whisper_result['segments'],
                        threshold=confidence_threshold
                    )
                    
                    if low_conf:
                        print(f"Found {len(low_conf)} low-confidence segments, retrying...")
                        retry_result = whisper_transcribe.retry_low_confidence_segments(
                            audio_path=audio_path,
                            segments=whisper_result['segments'],
                            current_model_name=model_size,
                            threshold=confidence_threshold
                        )
                        
                        if retry_result.get('improved'):
                            print(f"✓ Retry improved {retry_result.get('retry_count')} segments")
                            whisper_result['segments'] = retry_result['segments']
                            whisper_result['text'] = whisper_transcribe.format_segments_to_plain_text(
                                whisper_result['segments']
                            )
                
                # Store Whisper results
                segments = whisper_result.get('segments', [])
                
                # Format timestamps
                video_download.whisper_transcript = whisper_transcribe.format_segments_to_timestamped_text(segments)
                video_download.whisper_transcript_without_timestamps = whisper_result.get('text', '')
                
                # Translate to Hindi
                if whisper_result.get('text'):
                    print("Translating Whisper transcript to Hindi...")
                    hindi_translation = translate_text(whisper_result['text'], target='hi')
                    video_download.whisper_transcript_hindi = hindi_translation
                
                video_download.whisper_transcript_language = whisper_result.get('language', 'unknown')
                video_download.whisper_transcript_segments = segments  # Store raw segments JSON
                video_download.whisper_model_used = model_size
                
                # Calculate average confidence
                if segments:
                    avg_confidence = sum(seg.get('confidence', 0) for seg in segments) / len(segments)
                    video_download.whisper_confidence_avg = avg_confidence
                
                video_download.whisper_transcription_status = 'transcribed'
                video_download.whisper_transcript_processed_at = timezone.now()
                video_download.save()
                
                results['whisper_result'] = whisper_result
                print(f"✓ Whisper transcription successful: {len(whisper_result['text'])} chars")
            else:
                raise Exception(whisper_result.get('error', 'Unknown error'))
                
        finally:
            # Clean up audio file
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                    print(f"Cleaned up audio file: {audio_path}")
                except Exception as e:
                    print(f"Warning: Could not delete temp audio: {e}")
    
    except Exception as e:
        print(f"✗ Whisper transcription error: {e}")
        video_download.whisper_transcription_status = 'failed'
        video_download.whisper_transcript_error_message = str(e)
        video_download.save()
        import traceback
        traceback.print_exc()
    
    # ========== FINAL STATUS ==========
    print("\n" + "="*60)
    print("TRANSCRIPTION COMPARISON RESULTS")
    print("="*60)
    
    nca_success = results['nca_result'] and results['nca_result'].get('status') == 'success'
    whisper_success = results['whisper_result'] and results['whisper_result'].get('status') == 'success'
    
    if nca_success and whisper_success:
        results['status'] = 'success'
        print("✓ Both NCA and Whisper succeeded")
        print(f"  NCA: {len(results['nca_result'].get('text', ''))} chars")
        print(f"  Whisper: {len(results['whisper_result'].get('text', ''))} chars")
    elif nca_success or whisper_success:
        results['status'] = 'partial'
        print("⚠ Partial success:")
        print(f"  NCA: {'✓' if nca_success else '✗'}")
        print(f"  Whisper: {'✓' if whisper_success else '✗'}")
    else:
        results['status'] = 'failed'
        print("✗ Both transcription methods failed")
    
    print("="*60 + "\n")
    
    return results
