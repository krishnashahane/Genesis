"""Central, typed configuration. Single source of truth for runtime settings.

Settings are loaded from environment variables (prefixed ``GENESIS_``) and an
optional ``.env`` file. Every value has a safe default so the system boots with
zero configuration using in-memory fallbacks.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GENESIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- General ---
    env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    # --- API ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # --- Persistence backends (blank => in-memory fallback) ---
    redis_url: str = ""
    postgres_dsn: str = ""
    chroma_path: str = "./.genesis/chroma"

    # --- LLM provider ---
    llm_provider: Literal["mock", "anthropic", "gemini"] = "mock"
    llm_model: str = "claude-opus-4-8"
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")

    # --- Runtime tuning ---
    max_loop_iterations: int = 12
    task_concurrency: int = 4

    @property
    def use_redis(self) -> bool:
        return bool(self.redis_url)

    @property
    def use_postgres(self) -> bool:
        return bool(self.postgres_dsn)


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide cached Settings instance."""
    return Settings()
