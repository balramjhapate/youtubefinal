"""
FastAPI Application - Video Processing API
Replaces Django with FastAPI for better performance and automatic Swagger UI
"""
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
import os
from pathlib import Path

from app.database import init_db, get_db
from app.routers import videos, ai_settings, xtts, bulk, retry
from app.config import settings

# Create media directories
MEDIA_ROOT = Path("media")
MEDIA_ROOT.mkdir(exist_ok=True)
(MEDIA_ROOT / "videos").mkdir(exist_ok=True)
(MEDIA_ROOT / "voices").mkdir(exist_ok=True)
(MEDIA_ROOT / "synthesized_audio").mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print("🚀 Starting FastAPI application...")
    init_db()
    print("✅ Database initialized")
    print(f"📚 Swagger UI available at: http://localhost:{settings.PORT}/docs")
    print(f"📖 ReDoc available at: http://localhost:{settings.PORT}/redoc")
    yield
    # Shutdown
    print("👋 Shutting down FastAPI application...")


# Create FastAPI app
app = FastAPI(
    title="Video Processing API",
    description="""
    ## Video Processing API Documentation
    
    This API provides endpoints for:
    - **Video Extraction**: Extract videos from Xiaohongshu/RedNote URLs
    - **Transcription**: Transcribe videos using NCA Toolkit
    - **AI Processing**: Generate summaries and tags using AI
    - **Text-to-Speech**: Synthesize audio using Gemini TTS or XTTS
    - **Video Processing**: Download, process, and manage videos
    
    ### Features
    - Automatic Swagger UI documentation
    - RESTful API design
    - Background processing for long-running tasks
    - Support for multiple video sources
    
    ### Authentication
    Currently no authentication required (can be added later)
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (for media)
app.mount("/media", StaticFiles(directory="media"), name="media")

# Include routers
app.include_router(videos.router, prefix="/api", tags=["Videos"])
app.include_router(ai_settings.router, prefix="/api", tags=["AI Settings"])
app.include_router(xtts.router, prefix="/api", tags=["XTTS"])
app.include_router(bulk.router, prefix="/api", tags=["Bulk Operations"])
app.include_router(retry.router, prefix="/api", tags=["Retry Operations"])


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - API information"""
    return {
        "message": "Video Processing API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "video-processing-api"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )

