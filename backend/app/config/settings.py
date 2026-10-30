"""ECO-SHIELD Application Configuration."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "ECO-SHIELD"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = "sqlite:///./ecoshield.db"

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # File Upload Limits
    max_upload_size_mb: int = 50
    max_rows: int = 100000

    # Analysis
    default_timezone: str = "UTC"
    analysis_version: str = "1.0.0"

    # Report retention
    report_retention_days: int = 90

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
