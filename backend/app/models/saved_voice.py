"""
Saved Voice Model for XTTS
"""
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.models.base import Base


class SavedVoice(Base):
    """Saved Voice for XTTS"""
    __tablename__ = "saved_voice"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    file = Column(String(500))  # File path
    created_at = Column(DateTime, default=datetime.utcnow)

