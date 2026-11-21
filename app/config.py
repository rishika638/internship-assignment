from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 4000
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # LLM Providers Configuration
    PRIMARY_LLM_PROVIDER: str = "gemini"  # gemini, openai, claude, mock
    FALLBACK_LLM_PROVIDER: str = "mock"

    # Gemini
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Claude
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-haiku-20241022"

    # Mock Mode
    MOCK_MODE: bool = False

    # Cache
    CACHE_ENABLED: bool = True
    CACHE_DB_PATH: str = "data/cache.db"
    CACHE_TTL_SECONDS: int = 86400  # 24 hours

    # Crawler & Extraction limits
    REQUEST_TIMEOUT_SECONDS: float = 15.0
    MAX_REDIRECTS: int = 5
    MAX_PAGE_CONTENT_BYTES: int = 1048576  # 1MB
    MAX_CRAWL_SUBPAGES: int = 3
    MAX_BODY_TEXT_CHARS: int = 25000  # Token-efficient limit for LLM prompt

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

@lru_cache()
def get_settings() -> Settings:
    return Settings()
