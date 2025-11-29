"""
AI Provider Settings Model
"""
from sqlalchemy import Column, Integer, String
from app.models.base import Base


class AIProviderSettings(Base):
    """AI Provider Settings"""
    __tablename__ = "ai_provider_settings"
    
    id = Column(Integer, primary_key=True, default=1)
    provider = Column(String(20), default="gemini")
    api_key = Column(String(255), default="")

