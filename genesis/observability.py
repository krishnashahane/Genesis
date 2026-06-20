"""Observability layer: structured logging + lightweight in-process metrics.

Uses ``structlog`` when available, falling back to stdlib logging. Metrics are a
simple thread-safe counter/timer registry exposed via the API for dashboards.
"""

from __future__ import annotations

import logging
import sys
import threading
import time
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

try:  # pragma: no cover - exercised indirectly
    import structlog

    _HAS_STRUCTLOG = True
except ImportError:  # pragma: no cover
    _HAS_STRUCTLOG = False


def configure_logging(level: str = "INFO") -> None:
    """Configure global logging once at startup."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    # Logs go to stderr so stdout stays clean for CLI/JSON output.
    logging.basicConfig(format="%(message)s", stream=sys.stderr, level=log_level)
    if _HAS_STRUCTLOG:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(log_level),
            processors=[
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(),
            ],
            # Write to stderr so stdout is reserved for CLI/JSON payloads.
            logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
            cache_logger_on_first_use=True,
        )


def get_logger(name: str) -> Any:
    """Return a structured logger bound to ``name``."""
    if _HAS_STRUCTLOG:
        return structlog.get_logger(name)
    return logging.getLogger(name)


class Metrics:
    """Thread-safe, in-process metrics registry.

    Intentionally tiny and dependency-free so observability works everywhere.
    A production deployment can swap this for Prometheus/OTel without touching
    call sites — they only depend on ``incr`` / ``observe`` / ``snapshot``.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, float] = defaultdict(float)
        self._timers: dict[str, list[float]] = defaultdict(list)

    def incr(self, name: str, value: float = 1.0) -> None:
        with self._lock:
            self._counters[name] += value

    def observe(self, name: str, seconds: float) -> None:
        with self._lock:
            self._timers[name].append(seconds)

    @contextmanager
    def timer(self, name: str) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            self.observe(name, time.perf_counter() - start)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            timers = {
                k: {
                    "count": len(v),
                    "avg_ms": round(1000 * sum(v) / len(v), 3) if v else 0.0,
                    "max_ms": round(1000 * max(v), 3) if v else 0.0,
                }
                for k, v in self._timers.items()
            }
            return {"counters": dict(self._counters), "timers": timers}


# Process-wide metrics singleton.
METRICS = Metrics()
