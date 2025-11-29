"""
Video endpoints router
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.database import get_db, VideoDownload
from app.schemas import (
    VideoExtractRequest, VideoExtractResponse, VideoResponse,
    TranscriptionResponse, TranscriptionStatusResponse,
    AIProcessingResponse, AudioSynthesisResponse
)
from app.services.video_service import VideoService
from app.services.utils import perform_extraction, extract_video_id

router = APIRouter(prefix="/videos", tags=["Videos"])


@router.post("/extract/", response_model=VideoExtractResponse)
async def extract_video(
    request: VideoExtractRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Extract video from Xiaohongshu/RedNote URL
    
    - **url**: The video URL to extract
    - Returns video metadata and starts auto-processing in background
    """
    url = request.url
    
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    # Check for existing video by ID
    video_id = extract_video_id(url)
    if video_id:
        existing = db.query(VideoDownload).filter(VideoDownload.video_id == video_id).first()
        if existing:
            if existing.status == 'success':
                return VideoExtractResponse(
                    video_url=existing.video_url,
                    title=existing.title,
                    cover_url=existing.cover_url,
                    method=existing.extraction_method,
                    cached=True
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Video with ID '{video_id}' already exists but extraction failed."
                )
    
    # Check for duplicate
    if video_id and db.query(VideoDownload).filter(VideoDownload.video_id == video_id).exists():
        raise HTTPException(
            status_code=400,
            detail=f"Video with ID '{video_id}' already exists."
        )
    
    # Create pending download record
    download = VideoDownload(
        url=url,
        video_id=video_id,
        status='pending'
    )
    db.add(download)
    db.commit()
    db.refresh(download)
    
    # Try extraction
    video_data = perform_extraction(url)
    
    if video_data:
        # Update with success
        download.status = 'success'
        download.extraction_method = video_data.get('method', '')
        download.video_url = video_data.get('video_url', '')
        download.cover_url = video_data.get('cover_url', '')
        download.original_title = video_data.get('original_title', '')
        download.original_description = video_data.get('original_description', '')
        
        from app.services.utils import translate_text
        download.title = translate_text(download.original_title, target='en')
        download.description = translate_text(download.original_description, target='en')
        
        if video_data.get('duration'):
            download.duration = int(video_data.get('duration'))
        
        db.commit()
        
        # Start auto-processing in background
        background_tasks.add_task(
            VideoService.auto_process_video,
            download.id,
            db
        )
        
        return VideoExtractResponse(
            video_url=download.video_url,
            title=download.title,
            cover_url=download.cover_url,
            method=download.extraction_method,
            id=download.id,
            auto_processing=True,
            message="Video extracted. Auto-processing started in background."
        )
    else:
        download.status = 'failed'
        download.error_message = "Could not extract video. The link might be invalid or protected."
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="Could not extract video. The link might be invalid or protected."
        )


@router.get("/", response_model=List[VideoResponse])
async def list_videos(
    status: Optional[str] = Query(None),
    transcription_status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    List all videos with optional filtering
    
    - **status**: Filter by status (success, failed, pending)
    - **transcription_status**: Filter by transcription status
    - **search**: Search in video titles
    """
    query = db.query(VideoDownload)
    
    if status:
        query = query.filter(VideoDownload.status == status)
    if transcription_status:
        query = query.filter(VideoDownload.transcription_status == transcription_status)
    if search:
        query = query.filter(VideoDownload.title.contains(search))
    
    videos = query.order_by(VideoDownload.created_at.desc()).all()
    return videos


@router.get("/{video_id}/", response_model=VideoResponse)
async def get_video(video_id: int, db: Session = Depends(get_db)):
    """Get single video details by ID"""
    video = db.query(VideoDownload).filter(VideoDownload.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.post("/{video_id}/download/")
async def download_video(video_id: int, db: Session = Depends(get_db)):
    """Download video to local storage"""
    video = db.query(VideoDownload).filter(VideoDownload.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if not video.video_url:
        raise HTTPException(status_code=400, detail="No video URL found")
    
    from app.services.utils import download_file
    from pathlib import Path
    
    file_content = download_file(video.video_url)
    if file_content:
        # Save file
        media_dir = Path("media/videos")
        media_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{video.video_id or 'video'}_{video.id}.mp4"
        file_path = media_dir / filename
        
        with open(file_path, 'wb') as f:
            f.write(file_content.read())
        
        video.local_file = str(file_path)
        video.is_downloaded = True
        db.commit()
        
        return {"status": "success", "message": "Video downloaded successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to download video file")


@router.post("/{video_id}/transcribe/", response_model=TranscriptionResponse)
async def transcribe_video_endpoint(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start transcription with Hindi translation"""
    video = db.query(VideoDownload).filter(VideoDownload.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Update status
    video.transcription_status = 'transcribing'
    video.transcript_started_at = datetime.utcnow()
    db.commit()
    
    # Start transcription in background
    background_tasks.add_task(
        VideoService.transcribe_video_task,
        video_id,
        db
    )
    
    return TranscriptionResponse(
        status="processing",
        message="Transcription started in background"
    )


@router.get("/{video_id}/transcription_status/", response_model=TranscriptionStatusResponse)
async def get_transcription_status(video_id: int, db: Session = Depends(get_db)):
    """Get transcription status"""
    video = db.query(VideoDownload).filter(VideoDownload.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return TranscriptionStatusResponse(
        status=video.transcription_status,
        transcript=video.transcript,
        language=video.transcript_language
    )


@router.post("/{video_id}/process_ai/", response_model=AIProcessingResponse)
async def process_ai(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start AI processing to generate summary and tags"""
    video = db.query(VideoDownload).filter(VideoDownload.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    video.ai_processing_status = 'processing'
    db.commit()
    
    # Start AI processing in background
    background_tasks.add_task(
        VideoService.process_ai_task,
        video_id,
        db
    )
    
    return AIProcessingResponse(
        status="processing",
        message="AI processing started in background"
    )


@router.post("/{video_id}/synthesize/", response_model=AudioSynthesisResponse)
async def synthesize_audio(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Synthesize audio using Gemini TTS"""
    video = db.query(VideoDownload).filter(VideoDownload.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if not video.transcript_hindi:
        raise HTTPException(
            status_code=400,
            detail="No Hindi script available for synthesis"
        )
    
    # Start synthesis in background
    background_tasks.add_task(
        VideoService.synthesize_audio_task,
        video_id,
        db
    )
    
    return AudioSynthesisResponse(
        status="processing",
        message="Audio synthesis started in background"
    )


@router.post("/{video_id}/reprocess/")
async def reprocess_video(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Reprocess video - run full pipeline"""
    video = db.query(VideoDownload).filter(VideoDownload.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if not video.is_downloaded and not video.video_url:
        raise HTTPException(
            status_code=400,
            detail="Video must be downloaded or have a video URL to reprocess"
        )
    
    # Reset all processing states
    video.transcription_status = 'not_transcribed'
    video.transcript = ''
    video.transcript_hindi = ''
    video.ai_processing_status = 'not_processed'
    video.ai_summary = ''
    video.ai_tags = ''
    db.commit()
    
    # Start full pipeline in background
    background_tasks.add_task(
        VideoService.reprocess_video_task,
        video_id,
        db
    )
    
    return {
        "status": "processing_started",
        "message": "Reprocessing started in background",
        "video_id": video.id
    }


@router.delete("/{video_id}/delete/")
async def delete_video(video_id: int, db: Session = Depends(get_db)):
    """Delete video"""
    video = db.query(VideoDownload).filter(VideoDownload.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Delete local file if exists
    if video.local_file:
        from pathlib import Path
        file_path = Path(video.local_file)
        if file_path.exists():
            file_path.unlink()
    
    db.delete(video)
    db.commit()
    
    return {"status": "success", "message": "Video deleted"}

