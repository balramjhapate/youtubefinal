"""
Pydantic schemas package for request/response validation
"""
from app.schemas.video import (
    VideoExtractRequest,
    VideoExtractResponse,
    VideoResponse,
    VideoListResponse,
    VideoStatsResponse,
    TranscriptionResponse,
    TranscriptionStatusResponse,
    AIProcessingResponse,
    AudioSynthesisRequest,
    AudioSynthesisResponse,
)
from app.schemas.ai import (
    AISettingsResponse,
    AISettingsUpdate,
)
from app.schemas.xtts import (
    XTTSLanguageResponse,
    XTTSVoiceResponse,
    XTTSGenerateRequest,
    XTTSGenerateResponse,
)
from app.schemas.common import (
    BulkDeleteRequest,
    BulkDeleteResponse,
    RetryResponse,
)

__all__ = [
    # Video schemas
    "VideoExtractRequest",
    "VideoExtractResponse",
    "VideoResponse",
    "VideoListResponse",
    "VideoStatsResponse",
    "TranscriptionResponse",
    "TranscriptionStatusResponse",
    "AIProcessingResponse",
    "AudioSynthesisRequest",
    "AudioSynthesisResponse",
    # AI schemas
    "AISettingsResponse",
    "AISettingsUpdate",
    # XTTS schemas
    "XTTSLanguageResponse",
    "XTTSVoiceResponse",
    "XTTSGenerateRequest",
    "XTTSGenerateResponse",
    # Common schemas
    "BulkDeleteRequest",
    "BulkDeleteResponse",
    "RetryResponse",
]

