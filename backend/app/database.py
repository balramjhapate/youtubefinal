"""
Database configuration using SQLAlchemy with MySQL
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.pool import QueuePool
from datetime import datetime
from app.config import settings

# Create database engine with MySQL
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before using
    echo=False  # Set to True for SQL query logging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


# Models
class AIProviderSettings(Base):
    """AI Provider Settings"""
    __tablename__ = "ai_provider_settings"
    
    id = Column(Integer, primary_key=True, default=1)
    provider = Column(String(20), default="gemini")
    api_key = Column(String(255), default="")


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
    video_url = Column(String(1000), default="")
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


class SavedVoice(Base):
    """Saved Voice for XTTS"""
    __tablename__ = "saved_voice"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    file = Column(String(500))  # File path
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Initialize database - create tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

