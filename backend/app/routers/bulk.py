"""
Bulk operations router
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models import get_db, VideoDownload
from app.schemas import BulkDeleteRequest, BulkDeleteResponse

router = APIRouter(prefix="/bulk", tags=["Bulk Operations"])


@router.post("/delete/", response_model=BulkDeleteResponse)
async def bulk_delete_videos(
    request: BulkDeleteRequest,
    db: Session = Depends(get_db)
):
    """
    Delete multiple videos at once
    
    - **video_ids**: List of video IDs to delete
    """
    if not request.video_ids:
        raise HTTPException(status_code=400, detail="No video IDs provided")
    
    # Delete videos and their local files
    from pathlib import Path
    deleted_count = 0
    
    for video_id in request.video_ids:
        video = db.query(VideoDownload).filter(VideoDownload.id == video_id).first()
        if video:
            # Delete local file if exists
            if video.local_file:
                file_path = Path(video.local_file)
                if file_path.exists():
                    file_path.unlink()
            
            db.delete(video)
            deleted_count += 1
    
    db.commit()
    
    return BulkDeleteResponse(
        status="success",
        message=f"Deleted {deleted_count} video(s)",
        deleted_count=deleted_count
    )

