"""
Configuration settings for FastAPI application
"""
import os
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings"""
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*",  # Allow all origins in development
    ]
    
    # Database - MySQL
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "youtubefinal")
    
    @property
    def DATABASE_URL(self) -> str:
        """Construct MySQL database URL"""
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
    
    # Media
    MEDIA_ROOT: str = os.getenv("MEDIA_ROOT", "media")
    
    # NCA Toolkit API
    NCA_API_ENABLED: bool = os.getenv("NCA_API_ENABLED", "False").lower() == "true"
    NCA_API_URL: str = os.getenv("NCA_API_URL", "http://localhost:8080")
    NCA_API_KEY: str = os.getenv("NCA_API_KEY", "")
    NCA_API_TIMEOUT: int = int(os.getenv("NCA_API_TIMEOUT", "600"))
    
    # AI Provider (Gemini)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

