"""Memory Engine — unifies short-term (working) and long-term (vector) memory.

* **Short-term**: a bounded, per-session ring buffer of the most recent context.
  Fast, ephemeral, cleared between runs.
* **Long-term**: persistent, semantically searchable memory backed by the vector
  store. Survives across sessions — the "persistent memory" requirement.

Agents read recalled long-term memories + short-term context to make decisions,
and write new memories at the end of each loop iteration.
"""

from __future__ import annotations

from collections import deque

from genesis.core.event_bus import EventBus
from genesis.core.events import Event, EventType
from genesis.memory.types import MemoryRecord
from genesis.memory.vector_store import VectorStore, build_vector_store
from genesis.observability import METRICS, get_logger

log = get_logger("genesis.memory.engine")


class MemoryEngine:
    def __init__(
        self,
        bus: EventBus,
        chroma_path: str = "./.genesis/chroma",
        short_term_limit: int = 50,
        store: VectorStore | None = None,
    ) -> None:
        self._bus = bus
        self._store = store or build_vector_store(chroma_path)
        self._short_term: deque[MemoryRecord] = deque(maxlen=short_term_limit)

    # --- Short-term (working) memory ---
    def remember_short(self, content: str, **meta: object) -> MemoryRecord:
        rec = MemoryRecord(content=content, kind="working", metadata=dict(meta))
        self._short_term.append(rec)
        return rec

    def short_term(self, limit: int = 10) -> list[MemoryRecord]:
        return list(self._short_term)[-limit:]

    def clear_short(self) -> None:
        self._short_term.clear()

    # --- Long-term (persistent) memory ---
    async def store(
        self, content: str, kind: str = "episodic", tags: list[str] | None = None, **meta: object
    ) -> MemoryRecord:
        rec = MemoryRecord(content=content, kind=kind, tags=tags or [], metadata=dict(meta))
        self._store.add(rec)
        METRICS.incr("memory.stored")
        await self._bus.publish(
            Event(type=EventType.MEMORY_STORED, source="memory_engine",
                  payload={"kind": kind, "id": rec.id})
        )
        log.debug("memory.stored", kind=kind, id=rec.id)
        return rec

    def recall(self, query: str, k: int = 5, kind: str | None = None) -> list[MemoryRecord]:
        with METRICS.timer("memory.recall"):
            return self._store.query(query, k=k, kind=kind)

    @property
    def long_term_count(self) -> int:
        return self._store.count()
