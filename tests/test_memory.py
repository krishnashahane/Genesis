import pytest

from genesis.core.event_bus import EventBus
from genesis.memory.engine import MemoryEngine
from genesis.memory.vector_store import InMemoryVectorStore


@pytest.fixture
def memory() -> MemoryEngine:
    return MemoryEngine(EventBus(), store=InMemoryVectorStore())


async def test_short_term_is_bounded():
    mem = MemoryEngine(EventBus(), store=InMemoryVectorStore(), short_term_limit=3)
    for i in range(5):
        mem.remember_short(f"item {i}")
    items = mem.short_term(limit=10)
    assert len(items) == 3
    assert items[-1].content == "item 4"


async def test_store_and_recall(memory: MemoryEngine):
    await memory.store("Python is a programming language", kind="semantic")
    await memory.store("The cat sat on the mat", kind="semantic")
    results = memory.recall("programming language python", k=1)
    assert results
    assert "Python" in results[0].content
    assert results[0].score is not None


async def test_recall_filters_by_kind(memory: MemoryEngine):
    await memory.store("episodic note", kind="episodic")
    await memory.store("a learned lesson", kind="reflection")
    results = memory.recall("lesson", k=5, kind="reflection")
    assert all(r.kind == "reflection" for r in results)


async def test_store_emits_event():
    bus = EventBus()
    seen: list[str] = []

    async def h(e):
        seen.append(e.type)

    bus.subscribe("memory.stored", h)
    mem = MemoryEngine(bus, store=InMemoryVectorStore())
    await mem.store("remember this")
    assert "memory.stored" in seen
    assert mem.long_term_count == 1
