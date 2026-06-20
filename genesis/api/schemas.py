"""Request/response models for the REST API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    goal: str = Field(..., min_length=1, description="What the agent system should accomplish.")
    context: dict[str, Any] = Field(default_factory=dict)


class TaskRequest(BaseModel):
    goal: str = Field(..., min_length=1)
    priority: int = 0
    context: dict[str, Any] = Field(default_factory=dict)


class MemoryRequest(BaseModel):
    content: str
    kind: str = "semantic"
    tags: list[str] = Field(default_factory=list)


class RecallQuery(BaseModel):
    query: str
    k: int = 5
    kind: str | None = None


class ToolInvokeRequest(BaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict)
