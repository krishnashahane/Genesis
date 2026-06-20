"""Event model — the unit of communication on the Event Bus.

Everything in Genesis is event-driven: agents, the runtime, and observers all
react to typed events rather than calling each other directly. This keeps the
architecture decoupled and makes agent-to-agent communication observable.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EventType(StrEnum):
    """Well-known event types. The bus accepts arbitrary string topics too,
    so plugins can define their own without modifying the core enum."""

    # Lifecycle of the execution loop
    LOOP_STARTED = "loop.started"
    LOOP_FINISHED = "loop.finished"
    PHASE_STARTED = "phase.started"
    PHASE_FINISHED = "phase.finished"

    # Agent activity
    AGENT_STARTED = "agent.started"
    AGENT_FINISHED = "agent.finished"
    AGENT_MESSAGE = "agent.message"  # agent-to-agent communication
    AGENT_ERROR = "agent.error"

    # Task lifecycle
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_COMPLETED = "task.completed"

    # Memory & reflection
    MEMORY_STORED = "memory.stored"
    REFLECTION_CREATED = "reflection.created"

    # Tooling & permissions
    TOOL_INVOKED = "tool.invoked"
    PERMISSION_DENIED = "permission.denied"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Event(BaseModel):
    """An immutable record of something that happened in the system."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    type: str
    source: str = "system"
    timestamp: datetime = Field(default_factory=_utcnow)
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None  # ties events to a run / task

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"<Event {self.type} from={self.source}>"
