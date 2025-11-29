"""
Video service for background processing tasks
"""
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import VideoDownload, AIProviderSettings
from app.services.utils import (
    transcribe_video, translate_text, process_video_with_ai,
    download_file
)


class VideoService:
    """Service for video processing operations"""
    
    @staticmethod
    def auto_process_video(video_id: int, db: Session):
        """Auto-process video: download → transcribe → AI → script → TTS"""
        try:
            video = db.query(VideoDownload).filter(VideoDownload.id == video_id).first()
            if not video:
                return
            
            # Step 1: Download video
            print(f"🔄 Auto-processing: Downloading video {video.id}...")
            if video.video_url and not video.is_downloaded:
                file_content = download_file(video.video_url)
                if file_content:
                    from pathlib import Path
                    media_dir = Path("media/videos")
                    media_dir.mkdir(parents=True, exist_ok=True)
                    filename = f"{video.video_id or 'video'}_{video.id}.mp4"
                    file_path = media_dir / filename
                    
                    with open(file_path, 'wb') as f:
                        f.write(file_content.read())
                    
                    video.local_file = str(file_path)
                    video.is_downloaded = True
                    db.commit()
                    print(f"✓ Video downloaded: {filename}")
                else:
                    print(f"✗ Failed to download video")
                    return
            
            # Step 2: Transcribe
            if not video.transcript or video.transcription_status != 'transcribed':
                print(f"🔄 Auto-processing: Transcribing video {video.id}...")
                video.transcription_status = 'transcribing'
                video.transcript_started_at = datetime.utcnow()
                db.commit()
                
                result = transcribe_video(video)
                
                if result.get('status') == 'success':
                    video.transcript = result.get('text', '')
                    video.transcript_language = result.get('language', '')
                    video.transcription_status = 'transcribed'
                    video.transcript_processed_at = datetime.utcnow()
                    
                    if video.transcript:
                        try:
                            video.transcript_hindi = translate_text(video.transcript, target='hi')
                        except Exception as e:
                            print(f"Hindi translation failed: {e}")
                    
                    db.commit()
                    print(f"✓ Transcription completed")
                else:
                    video.transcription_status = 'failed'
                    video.transcript_error_message = result.get('error', 'Unknown error')
                    db.commit()
                    print(f"✗ Transcription failed")
                    return
            
            # Step 3: AI Processing
            print(f"🔄 Auto-processing: AI processing video {video.id}...")
            db.refresh(video)
            video.ai_processing_status = 'processing'
            db.commit()
            
            ai_result = process_video_with_ai(video)
            
            if ai_result['status'] == 'success':
                video.ai_processing_status = 'processed'
                video.ai_summary = ai_result.get('summary', '')
                video.ai_tags = ','.join(ai_result.get('tags', []))
                video.ai_processed_at = datetime.utcnow()
                db.commit()
                print(f"✓ AI processing completed")
            else:
                video.ai_processing_status = 'failed'
                video.ai_error_message = ai_result.get('error', 'Unknown error')
                db.commit()
                print(f"✗ AI processing failed")
                
        except Exception as e:
            import traceback
            print(f"✗ Auto-processing error: {str(e)}")
            traceback.print_exc()
            video = db.query(VideoDownload).filter(VideoDownload.id == video_id).first()
            if video and video.transcription_status == 'transcribing':
                video.transcription_status = 'failed'
                video.transcript_error_message = str(e)
                db.commit()
    
    @staticmethod
    def transcribe_video_task(video_id: int, db: Session):
        """Background task for transcription"""
        try:
            video = db.query(VideoDownload).filter(VideoDownload.id == video_id).first()
            if not video:
                return
            
            result = transcribe_video(video)
            
            if result['status'] == 'success':
                video.transcript = result['text']
                video.transcript_language = result['language']
                video.transcription_status = 'transcribed'
                video.transcript_processed_at = datetime.utcnow()
                
                if video.transcript:
                    try:
                        video.transcript_hindi = translate_text(video.transcript, target='hi')
                    except Exception as e:
                        print(f"Hindi translation failed: {e}")
                
                db.commit()
            else:
                video.transcription_status = 'failed'
                video.transcript_error_message = result.get('error', 'Unknown error')
                db.commit()
        except Exception as e:
            video = db.query(VideoDownload).filter(VideoDownload.id == video_id).first()
            if video:
                video.transcription_status = 'failed'
                video.transcript_error_message = str(e)
                db.commit()
    
    @staticmethod
    def process_ai_task(video_id: int, db: Session):
        """Background task for AI processing"""
        try:
            video = db.query(VideoDownload).filter(VideoDownload.id == video_id).first()
            if not video:
                return
            
            result = process_video_with_ai(video)
            
            if result['status'] == 'success':
                video.ai_summary = result['summary']
                video.ai_tags = ','.join(result['tags'])
                video.ai_processing_status = 'processed'
                video.ai_processed_at = datetime.utcnow()
                db.commit()
            else:
                video.ai_processing_status = 'failed'
                video.ai_error_message = result.get('error', 'Unknown error')
                db.commit()
        except Exception as e:
            video = db.query(VideoDownload).filter(VideoDownload.id == video_id).first()
            if video:
                video.ai_processing_status = 'failed'
                video.ai_error_message = str(e)
                db.commit()
    
    @staticmethod
    def synthesize_audio_task(video_id: int, db: Session):
        """Background task for audio synthesis"""
        try:
            video = db.query(VideoDownload).filter(VideoDownload.id == video_id).first()
            if not video:
                return
            
            if not video.transcript_hindi:
                return
            
            # Use Gemini TTS (simplified version)
            # Note: These imports may need to be adapted if legacy code is not available
            try:
                from legacy.root_debris.downloader.gemini_tts_service import GeminiTTSService
                from legacy.root_debris.downloader.utils import get_clean_script_for_tts
            except ImportError:
                print("Legacy TTS services not available. Skipping audio synthesis.")
                return
            
            clean_script = get_clean_script_for_tts(video.transcript_hindi)
            if not clean_script:
                return
            
            # Get AI settings
            settings_obj = db.query(AIProviderSettings).filter(AIProviderSettings.id == 1).first()
            if not settings_obj or not settings_obj.api_key:
                return
            
            service = GeminiTTSService(api_key=settings_obj.api_key)
            
            import tempfile
            temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            temp_audio_path = temp_audio.name
            temp_audio.close()
            
            service.generate_speech(
                text=clean_script,
                language_code='hi-IN',
                voice_name='Enceladus',
                output_path=temp_audio_path,
                video_duration=video.duration or 0
            )
            
            # Save audio file
            from pathlib import Path
            media_dir = Path("media/synthesized_audio")
            media_dir.mkdir(parents=True, exist_ok=True)
            output_path = media_dir / f"synthesized_{video.id}.mp3"
            
            import shutil
            shutil.move(temp_audio_path, str(output_path))
            
            # Note: In a full implementation, you'd save this path to the database
            # For now, we'll just mark it as completed
            
        except Exception as e:
            import traceback
            print(f"TTS synthesis error: {e}")
            traceback.print_exc()
    
    @staticmethod
    def reprocess_video_task(video_id: int, db: Session):
        """Background task for full video reprocessing"""
        # This runs the full pipeline: transcribe → AI → (script → TTS if legacy model)
        VideoService.transcribe_video_task(video_id, db)
        VideoService.process_ai_task(video_id, db)

