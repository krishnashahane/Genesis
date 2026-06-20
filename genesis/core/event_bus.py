"""Event Bus — asynchronous publish/subscribe backbone.

Default implementation is a fully in-process asyncio bus (zero dependencies).
When ``GENESIS_REDIS_URL`` is set, events are additionally mirrored to a Redis
pub/sub channel so multiple Genesis workers can share one event stream. The
public API is identical regardless of backend, so call sites never change.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from genesis.core.events import Event
from genesis.observability import METRICS, get_logger

log = get_logger("genesis.event_bus")

Handler = Callable[[Event], Awaitable[None]]


class EventBus:
    """In-process async pub/sub with an optional Redis mirror.

    Subscriptions are keyed by topic (the event ``type``). The special topic
    ``"*"`` receives every event — used by the observability layer and the
    Web UI's live feed.
    """

    def __init__(self, redis_url: str = "") -> None:
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)
        self._history: list[Event] = []
        self._history_limit = 1000
        self._redis_url = redis_url
        self._redis: Any | None = None

    async def connect(self) -> None:
        """Lazily connect the optional Redis mirror."""
        if not self._redis_url:
            return
        try:  # pragma: no cover - requires redis
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
            await self._redis.ping()
            log.info("event_bus.redis_connected", url=self._redis_url)
        except Exception as exc:  # pragma: no cover
            log.warning("event_bus.redis_unavailable", error=str(exc))
            self._redis = None

    def subscribe(self, topic: str, handler: Handler) -> Callable[[], None]:
        """Register ``handler`` for ``topic``. Returns an unsubscribe callback."""
        self._subscribers[topic].append(handler)

        def _unsub() -> None:
            if handler in self._subscribers[topic]:
                self._subscribers[topic].remove(handler)

        return _unsub

    async def publish(self, event: Event) -> None:
        """Deliver ``event`` to all matching subscribers concurrently."""
        METRICS.incr("events.published")
        self._record(event)
        log.debug("event.published", type=event.type, source=event.source)

        handlers = [*self._subscribers.get(event.type, []), *self._subscribers.get("*", [])]
        if handlers:
            results = await asyncio.gather(
                *(h(event) for h in handlers), return_exceptions=True
            )
            for r in results:
                if isinstance(r, Exception):  # a bad subscriber must not break the bus
                    METRICS.incr("events.handler_errors")
                    log.error("event.handler_error", type=event.type, error=str(r))

        if self._redis is not None:  # pragma: no cover - requires redis
            try:
                await self._redis.publish("genesis.events", event.model_dump_json())
            except Exception as exc:
                log.warning("event_bus.redis_publish_failed", error=str(exc))

    def _record(self, event: Event) -> None:
        self._history.append(event)
        if len(self._history) > self._history_limit:
            self._history = self._history[-self._history_limit :]

    def history(self, limit: int = 100, topic: str | None = None) -> list[Event]:
        """Return recent events, optionally filtered by topic."""
        items = self._history if topic is None else [e for e in self._history if e.type == topic]
        return items[-limit:]

    async def close(self) -> None:
        if self._redis is not None:  # pragma: no cover
            await self._redis.aclose()
