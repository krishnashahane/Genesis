"""Central, typed configuration for Genesis."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GENESIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    # API
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_key: str = ""
    cors_origins: str = ""
    max_request_bytes: int = 1_000_000
    rate_limit_per_minute: int = 30

    # Optional infrastructure
    redis_url: str = ""
    chroma_path: str = "./.genesis/chroma"

    # LLM
    llm_provider: Literal["mock", "anthropic", "gemini"] = "mock"
    llm_model: str = "claude-sonnet-5-5"
    anthropic_api_key: str = ""
    gemini_api_key: str = ""

    @property
    def anthropic_model(self) -> str:
        return self.llm_model or "claude-sonnet-5-5"

    @property
    def gemini_model(self) -> str:
        return self.llm_model if self.llm_model.startswith("gemini-") else "gemini-3.8-flash"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @lru_cache
    def _validated_placeholder(self) -> bool:
        return True


@lru_cache
def get_settings() -> Settings:
    return Settings()
