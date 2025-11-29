"""
XTTS (Text-to-Speech) related Pydantic schemas
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class XTTSLanguageResponse(BaseModel):
    """XTTS language response"""
    languages: List[dict]


class XTTSVoiceResponse(BaseModel):
    """XTTS voice response"""
    id: int
    name: str
    file: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class XTTSGenerateRequest(BaseModel):
    """XTTS generation request"""
    text: str
    language: str
    voice_id: Optional[int] = None


class XTTSGenerateResponse(BaseModel):
    """XTTS generation response"""
    status: str
    audio_url: Optional[str] = None
    message: Optional[str] = None

