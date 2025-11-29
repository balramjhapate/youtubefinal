"""
Database compatibility shim - redirects to new models package
DEPRECATED: Use app.models instead
"""
import warnings

warnings.warn(
    "app.database is deprecated. Use app.models instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import from models for backward compatibility
from app.models import (
    Base,
    engine,
    SessionLocal,
    get_db,
    init_db,
    VideoDownload,
    AIProviderSettings,
    SavedVoice,
)

__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "init_db",
    "VideoDownload",
    "AIProviderSettings",
    "SavedVoice",
]

