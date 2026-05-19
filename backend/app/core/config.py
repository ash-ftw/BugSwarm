from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_origin: str = "http://localhost:5173"
    cors_origins_raw: str | None = Field(default=None, alias="CORS_ORIGINS")

    database_url: str = "postgresql+psycopg://bugswarm:bugswarm@localhost:5432/bugswarm"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me-before-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    artifact_storage_root: str = "storage"

    ai_free_mode: bool = True
    groq_api_key: str = ""
    groq_model: str = "qwen/qwen3-32b"
    gptoss_base_url: str = "http://localhost:11434/v1"
    gptoss_model: str = "gpt-oss-20b"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash-lite"

    default_agent_count: int = 3
    default_max_depth: int = 3
    default_max_duration_minutes: int = 30
    max_agent_count: int = 8

    @property
    def cors_origins(self) -> list[str]:
        if self.cors_origins_raw:
            return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]
        return [self.frontend_origin]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
