from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://bugswarm:bugswarm@localhost:5432/bugswarm"
    redis_url: str = "redis://localhost:6379/0"
    artifact_storage_root: str = "storage"

    ai_free_mode: bool = True
    groq_api_key: str = ""
    groq_model: str = "qwen/qwen3-32b"
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "openrouter/auto"
    gptoss_base_url: str = "http://localhost:11434/v1"
    gptoss_model: str = "gpt-oss-20b"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash-lite"

    default_agent_count: int = 3
    default_max_depth: int = 3
    default_max_duration_minutes: int = 30
    max_agent_count: int = 8


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()


settings = get_settings()
