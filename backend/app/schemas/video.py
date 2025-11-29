"""
Video-related Pydantic schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class VideoExtractRequest(BaseModel):
    """Request to extract video from URL"""
    url: str = Field(..., description="Xiaohongshu/RedNote video URL")


class VideoResponse(BaseModel):
    """Video response model"""
    id: int
    url: str
    title: str
    original_title: str
    description: str
    cover_url: str
    video_url: str
    status: str
    transcription_status: str
    ai_processing_status: str
    audio_prompt_status: str
    transcript_hindi: str
    is_downloaded: bool
    extraction_method: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class VideoExtractResponse(BaseModel):
    """Video extraction response"""
    video_url: str
    title: str
    cover_url: str
    method: str
    id: Optional[int] = None
    cached: Optional[bool] = False
    auto_processing: Optional[bool] = False
    message: Optional[str] = None


class VideoListResponse(BaseModel):
    """List of videos response"""
    videos: List[VideoResponse]


class TranscriptionResponse(BaseModel):
    """Transcription response"""
    status: str
    message: str
    transcript: Optional[str] = None
    transcript_hindi: Optional[str] = None
    language: Optional[str] = None


class TranscriptionStatusResponse(BaseModel):
    """Transcription status response"""
    status: str
    transcript: Optional[str] = None
    language: Optional[str] = None


class AIProcessingResponse(BaseModel):
    """AI Processing response"""
    status: str
    message: str
    summary: Optional[str] = None
    tags: Optional[str] = None


class AudioSynthesisRequest(BaseModel):
    """Audio synthesis request"""
    profile_id: Optional[int] = None
    text: Optional[str] = None


class AudioSynthesisResponse(BaseModel):
    """Audio synthesis response"""
    status: str
    message: str
    audio_url: Optional[str] = None
    clean_script: Optional[str] = None


class VideoStatsResponse(BaseModel):
    """Video statistics response"""
    total: int
    downloaded: int
    cloud: int
    success: int
    failed: int
    pending: int

