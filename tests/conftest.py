"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from genesis.config import Settings
from genesis.core.runtime import Runtime


@pytest.fixture
def settings() -> Settings:
    return Settings(env="test", llm_provider="mock", redis_url="", postgres_dsn="")


@pytest.fixture
async def runtime(settings: Settings) -> Runtime:
    rt = Runtime(settings)
    await rt.start()
    try:
        yield rt
    finally:
        await rt.stop()
