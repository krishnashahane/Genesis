"""Task Queue — durable-ish work items consumed by the runtime.

In-memory ``asyncio`` queue by default; emits lifecycle events on the bus so the
Observability layer and Web UI can track work. Designed so a Redis/Postgres
backend can be dropped in behind the same interface later.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from genesis.core.event_bus import EventBus
from genesis.core.events import Event, EventType


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    goal: str
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 0  # higher = sooner
    context: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TaskQueue:
    """Priority-ordered async task queue with an event-emitting state store."""

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._tasks: dict[str, Task] = {}
        self._ready: asyncio.PriorityQueue[tuple[int, float, str]] = asyncio.PriorityQueue()
        self._seq = 0

    async def submit(self, task: Task) -> Task:
        self._tasks[task.id] = task
        self._seq += 1
        # negate priority so higher priority dequeues first; seq breaks ties (FIFO)
        await self._ready.put((-task.priority, self._seq, task.id))
        await self._bus.publish(
            Event(type=EventType.TASK_CREATED, source="task_queue",
                  correlation_id=task.id, payload={"goal": task.goal})
        )
        return task

    async def claim(self) -> Task:
        """Block until a task is available, mark it RUNNING, and return it."""
        _, _, task_id = await self._ready.get()
        task = self._tasks[task_id]
        await self._update(task, TaskStatus.RUNNING)
        return task

    async def complete(self, task_id: str, result: dict[str, Any]) -> Task:
        task = self._tasks[task_id]
        task.result = result
        await self._update(task, TaskStatus.COMPLETED, EventType.TASK_COMPLETED)
        return task

    async def fail(self, task_id: str, error: str) -> Task:
        task = self._tasks[task_id]
        task.error = error
        await self._update(task, TaskStatus.FAILED)
        return task

    async def _update(
        self, task: Task, status: TaskStatus, event: str = EventType.TASK_UPDATED
    ) -> None:
        task.status = status
        task.updated_at = datetime.now(UTC)
        await self._bus.publish(
            Event(type=event, source="task_queue", correlation_id=task.id,
                  payload={"status": status.value})
        )

    def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def all(self) -> list[Task]:
        return list(self._tasks.values())

    @property
    def pending(self) -> int:
        return self._ready.qsize()
