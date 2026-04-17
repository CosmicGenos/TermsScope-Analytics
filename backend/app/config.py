"""Application configuration via environment variables."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────
    app_name: str = "TermsScope Analytics"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me-to-a-random-secret-key"

    # ── Database ──────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/termsscope"
    database_url_sync: str = "postgresql+psycopg://postgres:postgres@localhost:5432/termsscope"

    # ── Redis ─────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 86400  # 24 hours

    # ── LLM ───────────────────────────────────────────────
    default_llm_provider: str = "openai"
    default_llm_model: str = "gpt-4o-mini"
    openai_api_key: str = ""
    google_api_key: str = ""
    anthropic_api_key: str = ""

    # ── Google OAuth ──────────────────────────────────────
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"

    # ── Frontend / CORS ───────────────────────────────────
    frontend_url: str = "http://localhost:5173"
    cors_origins: str = '["http://localhost:5173","http://localhost:3000"]'

    # ── Rate Limiting ─────────────────────────────────────
    rate_limit_per_hour: int = 10
    max_token_limit: int = 100_000
    max_file_size_mb: int = 10

    @property
    def cors_origin_list(self) -> List[str]:
        """Parse CORS origins from JSON string."""
        try:
            return json.loads(self.cors_origins)
        except (json.JSONDecodeError, TypeError):
            return [self.frontend_url]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached singleton for application settings."""
    return Settings()
