"""
Video Download Model
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from datetime import datetime
from app.models.base import Base


class VideoDownload(Base):
    """Video Download Model"""
    __tablename__ = "video_download"
    
    # Core fields
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(500))
    video_id = Column(String(100), unique=True, nullable=True, index=True)
    
    # Content
    title = Column(String(500), default="")
    original_title = Column(String(500), default="")
    description = Column(Text, default="")
    original_description = Column(Text, default="")
    
    # Media
    video_url = Column(Text, default="")  # Changed from String(1000) to Text for long YouTube URLs
    cover_url = Column(String(1000), default="")
    local_file = Column(String(500), nullable=True)  # File path
    is_downloaded = Column(Boolean, default=False)
    duration = Column(Integer, default=0)
    
    # Metadata
    extraction_method = Column(String(20), default="")
    status = Column(String(20), default="pending")  # success, failed, pending
    error_message = Column(Text, default="")
    
    # AI Processing
    ai_processing_status = Column(String(20), default="not_processed")
    ai_processed_at = Column(DateTime, nullable=True)
    ai_summary = Column(Text, default="")
    ai_tags = Column(String(500), default="")
    ai_error_message = Column(Text, default="")
    
    # Transcription
    transcription_status = Column(String(20), default="not_transcribed")
    transcript = Column(Text, default="")
    transcript_hindi = Column(Text, default="")
    transcript_language = Column(String(10), default="")
    transcript_started_at = Column(DateTime, nullable=True)
    transcript_processed_at = Column(DateTime, nullable=True)
    transcript_error_message = Column(Text, default="")
    
    # Audio Prompt
    audio_prompt_status = Column(String(20), default="not_generated")
    audio_generation_prompt = Column(Text, default="")
    audio_prompt_generated_at = Column(DateTime, nullable=True)
    audio_prompt_error = Column(Text, default="")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

