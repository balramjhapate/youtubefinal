#!/usr/bin/env python3
"""
FastAPI Application Runner
Run this instead of Django manage.py runserver
"""
import uvicorn
from app.main import app
from app.config import settings

if __name__ == "__main__":
    print("🚀 Starting FastAPI Video Processing API...")
    print(f"📚 Swagger UI: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"📖 ReDoc: http://{settings.HOST}:{settings.PORT}/redoc")
    print(f"🌐 API Base: http://{settings.HOST}:{settings.PORT}/api")
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )

