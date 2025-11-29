"""
AI Settings endpoints router
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models import get_db, AIProviderSettings
from app.schemas import AISettingsResponse, AISettingsUpdate

router = APIRouter(prefix="/ai-settings", tags=["AI Settings"])


@router.get("/", response_model=AISettingsResponse)
async def get_ai_settings(db: Session = Depends(get_db)):
    """
    Get current AI provider settings
    
    Returns the current AI provider configuration (Gemini, OpenAI, etc.)
    """
    settings = db.query(AIProviderSettings).filter(AIProviderSettings.id == 1).first()
    if not settings:
        # Create default settings
        settings = AIProviderSettings(id=1, provider="gemini", api_key="")
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return AISettingsResponse(
        provider=settings.provider,
        api_key=settings.api_key
    )


@router.post("/", response_model=dict)
async def update_ai_settings(
    request: AISettingsUpdate,
    db: Session = Depends(get_db)
):
    """
    Update AI provider settings
    
    - **provider**: AI provider name (gemini, openai, anthropic)
    - **api_key**: API key for the provider
    """
    settings = db.query(AIProviderSettings).filter(AIProviderSettings.id == 1).first()
    
    if not settings:
        settings = AIProviderSettings(
            id=1,
            provider=request.provider,
            api_key=request.api_key
        )
        db.add(settings)
    else:
        settings.provider = request.provider
        settings.api_key = request.api_key
    
    db.commit()
    
    return {"status": "saved"}

