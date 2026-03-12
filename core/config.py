"""
Configuration settings for the Neuro-Symbolic RAG System.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False
    )
    
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # OpenRouter Configuration
    OPENROUTER_API_KEY: Optional[str] = None
    
    # ChromaDB Configuration
    CHROMA_DB_PATH: str = "./storage/chromadb"
    
    # Model Configuration
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    DEFAULT_LLM_MODEL: str = "meta-llama/llama-3-8b-instruct:free"
    FALLBACK_LLM_MODEL: str = "google/gemma-7b-it:free"
    
    # Processing Configuration
    MAX_PDF_SIZE: int = 50 * 1024 * 1024  # 50MB
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    MAX_CONCURRENT_DOWNLOADS: int = 5
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0
    MAX_AGE_YEARS: int = 5  # Default filter for papers older than 5 years
    
    # API Keys
    ARXIV_API_KEY: Optional[str] = None


settings = Settings()