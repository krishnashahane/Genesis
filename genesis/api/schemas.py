"""Request/response models for the REST API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    goal: str = Field(..., min_length=1, max_length=20_000, description="What the agent system should accomplish.")
    context: dict[str, Any] = Field(default_factory=dict)


class TaskRequest(BaseModel):
    goal: str = Field(..., min_length=1, max_length=20_000)
    priority: int = Field(default=0, ge=-100, le=100)
    context: dict[str, Any] = Field(default_factory=dict)


class MemoryRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=50_000)
    kind: str = Field(default="semantic", min_length=1, max_length=32)
    tags: list[str] = Field(default_factory=list, max_length=50)


class RecallQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=20_000)
    k: int = Field(default=5, ge=1, le=50)
    kind: str | None = None


class ToolInvokeRequest(BaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict)
