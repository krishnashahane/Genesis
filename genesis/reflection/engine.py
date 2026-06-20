"""Reflection Engine — turns iteration outcomes into durable, reusable lessons.

This closes the self-improvement loop: after each run the engine persists a
``reflection`` memory and emits an event. On future runs, agents recall these
reflections (via the Memory Engine) and adjust behaviour — without any code
change or hardcoded rule.
"""

from __future__ import annotations

from genesis.core.event_bus import EventBus
from genesis.core.events import Event, EventType
from genesis.memory.engine import MemoryEngine
from genesis.memory.types import MemoryRecord
from genesis.observability import get_logger

log = get_logger("genesis.reflection")


class ReflectionEngine:
    def __init__(self, memory: MemoryEngine, bus: EventBus) -> None:
        self._memory = memory
        self._bus = bus

    async def reflect(
        self, goal: str, summary: str, correlation_id: str | None = None
    ) -> MemoryRecord:
        content = f"Lesson from goal '{goal}': {summary}"
        record = await self._memory.store(content, kind="reflection", tags=["lesson"])
        await self._bus.publish(
            Event(type=EventType.REFLECTION_CREATED, source="reflection_engine",
                  correlation_id=correlation_id, payload={"memory_id": record.id})
        )
        log.info("reflection.created", id=record.id)
        return record

    def past_lessons(self, goal: str, k: int = 5) -> list[MemoryRecord]:
        return self._memory.recall(goal, k=k, kind="reflection")
