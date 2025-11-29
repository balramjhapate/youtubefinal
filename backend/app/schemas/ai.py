"""
AI-related Pydantic schemas
"""
from pydantic import BaseModel, Field


class AISettingsResponse(BaseModel):
    """AI Settings response"""
    provider: str
    api_key: str


class AISettingsUpdate(BaseModel):
    """AI Settings update request"""
    provider: str = Field(default="gemini")
    api_key: str = Field(default="")

