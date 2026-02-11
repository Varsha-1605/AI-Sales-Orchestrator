"""
Configuration settings for AI Sales Orchestrator
"""

from pydantic_settings import BaseSettings
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # API Configuration
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    
    # Server Configuration
    FASTAPI_HOST: str = os.getenv("FASTAPI_HOST", "0.0.0.0")
    FASTAPI_PORT: int = int(os.getenv("FASTAPI_PORT", "8000"))
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "True").lower() == "true"
    
    # CORS Settings
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]
    
    # Session Settings
    SESSION_TIMEOUT: int = int(os.getenv("SESSION_TIMEOUT", "3600"))
    MAX_MEMORY_SIZE: int = int(os.getenv("MAX_MEMORY_SIZE", "1000"))
    
    # Data Paths
    DATA_DIR: str = "data"
    PRODUCTS_FILE: str = "data/products.json"
    CUSTOMERS_FILE: str = "data/customers.json"
    STORES_FILE: str = "data/stores.json"
    SESSIONS_FILE: str = "data/sessions.json"
    
    # Mock Mode (fallback when API key not available)
    USE_MOCK_RESPONSES: bool = not bool(ANTHROPIC_API_KEY)
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()