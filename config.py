"""Configuration module for Talk to Your Data."""
import os
from dataclasses import dataclass


@dataclass
class Config:
    """Configuration container for the application."""
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    READONLY: bool = True
    STATEMENT_TIMEOUT_MS: int = 5000
    
    # Gemini / LLM
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GENAI_MODEL_ID: str = os.getenv("GENAI_MODEL_ID", "gemini-1.5-flash")
    LLM_TIMEOUT_S: float = 10.0
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_OUTPUT_TOKENS: int = 1024
    
    # Query constraints
    MAX_LIMIT: int = 1000
    DEFAULT_LIMIT: int = 100
    
    # Feature flags
    ENABLE_RBAC: bool = True
    ENABLE_LOGGING: bool = True
    ENABLE_SCHEMA_CACHE: bool = True
    SCHEMA_CACHE_TTL_S: int = 3600
    
    # Dev fallback for testing without LLM
    DEV_FALLBACK_MODE: bool = os.getenv("DEV_FALLBACK_MODE", "false").lower() == "true"


def get_config() -> Config:
    """Load and return the global configuration."""
    return Config()
