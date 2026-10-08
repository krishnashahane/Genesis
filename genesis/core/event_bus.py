"""Async in-process event bus with an optional Redis mirror."""

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
    def __init__(self, redis_url: str = "") -> None:
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)
        self._history: list[Event] = []
        self._history_limit = 1000
        self._redis_url = redis_url
        self._redis: Any | None = None

    async def connect(self) -> None:
        if not self._redis_url:
            return
        try:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
            await self._redis.ping()
            log.info("event_bus.redis_connected")
        except Exception as exc:  # pragma: no cover - requires Redis
            log.warning("event_bus.redis_unavailable", error=str(exc))
            self._redis = None

    def subscribe(self, topic: str, handler: Handler) -> Callable[[], None]:
        self._subscribers[topic].append(handler)

        def _unsub() -> None:
            if handler in self._subscribers[topic]:
                self._subscribers[topic].remove(handler)

        return _unsub

    async def publish(self, event: Event) -> None:
        METRICS.incr("events.published")
        self._record(event)

        handlers = [
            *self._subscribers.get(event.type, []),
            *self._subscribers.get("*", []),
        ]
        if handlers:
            results = await asyncio.gather(
                *(handler(event) for handler in handlers),
                return_exceptions=True,
            )
            for result in results:
                if isinstance(result, Exception):
                    METRICS.incr("events.handler_errors")
                    log.error(
                        "event.handler_error",
                        type=event.type,
                        error=str(result),
                    )

        if self._redis is not None:  # pragma: no cover - requires Redis
            try:
                await self._redis.publish(
                    "genesis.events",
                    event.model_dump_json(),
                )
            except Exception as exc:
                log.warning("event_bus.redis_publish_failed", error=str(exc))

    def _record(self, event: Event) -> None:
        self._history.append(event)
        if len(self._history) > self._history_limit:
            self._history = self._history[-self._history_limit :]

    def history(self, limit: int = 100, topic: str | None = None) -> list[Event]:
        items = (
            self._history
            if topic is None
            else [event for event in self._history if event.type == topic]
        )
        return items[-limit:]

    async def close(self) -> None:
        if self._redis is not None:  # pragma: no cover - requires Redis
            await self._redis.aclose()
            self._redis = None
