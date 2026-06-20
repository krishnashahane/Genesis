"""Shared memory data types."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class MemoryRecord(BaseModel):
    """A single persisted memory (episodic, semantic, or reflective)."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    content: str
    kind: str = "episodic"  # episodic | semantic | reflection
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    score: float | None = None  # relevance score, filled on retrieval
