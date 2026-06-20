
from genesis.core.event_bus import EventBus
from genesis.core.events import Event, EventType


async def test_publish_delivers_to_subscriber():
    bus = EventBus()
    received: list[Event] = []

    async def handler(e: Event):
        received.append(e)

    bus.subscribe(EventType.TASK_CREATED, handler)
    await bus.publish(Event(type=EventType.TASK_CREATED, payload={"x": 1}))

    assert any(e.payload.get("x") == 1 for e in received)


async def test_wildcard_subscriber_receives_all():
    bus = EventBus()
    seen: list[str] = []

    async def all_handler(e: Event):
        seen.append(e.type)

    bus.subscribe("*", all_handler)
    await bus.publish(Event(type=EventType.AGENT_STARTED))
    await bus.publish(Event(type=EventType.MEMORY_STORED))

    assert seen == [EventType.AGENT_STARTED, EventType.MEMORY_STORED]


async def test_bad_handler_does_not_break_bus():
    bus = EventBus()
    ok: list[int] = []

    async def bad(e: Event):
        raise RuntimeError("boom")

    async def good(e: Event):
        ok.append(1)

    bus.subscribe(EventType.TASK_CREATED, bad)
    bus.subscribe(EventType.TASK_CREATED, good)
    await bus.publish(Event(type=EventType.TASK_CREATED))

    assert ok == [1]  # good handler still ran


async def test_history_and_filter():
    bus = EventBus()
    await bus.publish(Event(type=EventType.AGENT_STARTED))
    await bus.publish(Event(type=EventType.AGENT_FINISHED))
    assert len(bus.history()) == 2
    assert len(bus.history(topic=EventType.AGENT_STARTED)) == 1


async def test_unsubscribe():
    bus = EventBus()
    seen: list[int] = []

    async def h(e: Event):
        seen.append(1)

    unsub = bus.subscribe(EventType.TASK_CREATED, h)
    unsub()
    await bus.publish(Event(type=EventType.TASK_CREATED))
    assert seen == []
