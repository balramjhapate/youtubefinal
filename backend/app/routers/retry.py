"""
Retry operations router for failed pipeline steps
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.models import get_db, VideoDownload
from app.schemas import RetryResponse
from app.services.video_service import VideoService

router = APIRouter(prefix="/videos/{video_id}/retry", tags=["Retry Operations"])


@router.post("/transcription/", response_model=RetryResponse)
async def retry_transcription(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Retry failed transcription step"""
    video = db.query(VideoDownload).filter(VideoDownload.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video.transcription_status != 'failed':
        raise HTTPException(
            status_code=400,
            detail=f"Transcription has not failed. Current status: {video.transcription_status}"
        )
    
    # Reset and retry
    video.transcription_status = 'not_transcribed'
    video.transcript_error_message = ''
    db.commit()
    
    background_tasks.add_task(
        VideoService.transcribe_video_task,
        video_id,
        db
    )
    
    return RetryResponse(
        status="processing",
        message="Transcription retry started"
    )


@router.post("/ai-processing/", response_model=RetryResponse)
async def retry_ai_processing(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Retry failed AI processing step"""
    video = db.query(VideoDownload).filter(VideoDownload.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video.ai_processing_status != 'failed':
        raise HTTPException(
            status_code=400,
            detail=f"AI processing has not failed. Current status: {video.ai_processing_status}"
        )
    
    video.ai_processing_status = 'not_processed'
    video.ai_error_message = ''
    db.commit()
    
    background_tasks.add_task(
        VideoService.process_ai_task,
        video_id,
        db
    )
    
    return RetryResponse(
        status="processing",
        message="AI processing retry started"
    )


@router.post("/script-generation/", response_model=RetryResponse)
async def retry_script_generation(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Retry failed script generation step"""
    # This endpoint exists for compatibility but script generation
    # is handled in the legacy model, so we'll return a message
    return RetryResponse(
        status="not_implemented",
        message="Script generation retry - handled in legacy model"
    )


@router.post("/tts-synthesis/", response_model=RetryResponse)
async def retry_tts_synthesis(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Retry failed TTS synthesis step"""
    video = db.query(VideoDownload).filter(VideoDownload.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if not video.transcript_hindi:
        raise HTTPException(
            status_code=400,
            detail="No Hindi script available for synthesis"
        )
    
    background_tasks.add_task(
        VideoService.synthesize_audio_task,
        video_id,
        db
    )
    
    return RetryResponse(
        status="processing",
        message="TTS synthesis retry started"
    )


@router.post("/final-video/", response_model=RetryResponse)
async def retry_final_video(
    video_id: int,
    db: Session = Depends(get_db)
):
    """Retry failed final video creation step"""
    # This is handled in legacy model
    return RetryResponse(
        status="not_implemented",
        message="Final video retry - handled in legacy model"
    )


@router.post("/cloudinary-upload/", response_model=RetryResponse)
async def retry_cloudinary_upload(
    video_id: int,
    db: Session = Depends(get_db)
):
    """Retry failed Cloudinary upload"""
    return RetryResponse(
        status="not_implemented",
        message="Cloudinary upload retry - not implemented"
    )


@router.post("/google-sheets-sync/", response_model=RetryResponse)
async def retry_google_sheets_sync(
    video_id: int,
    db: Session = Depends(get_db)
):
    """Retry failed Google Sheets sync"""
    return RetryResponse(
        status="not_implemented",
        message="Google Sheets sync retry - not implemented"
    )

