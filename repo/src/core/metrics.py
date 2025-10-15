"""Lightweight metrics collection helpers for the worker loop."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

# Functions
# ---------
# - MetricsState
# - flush_metrics

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MetricsState:
    """In-memory metrics store with periodic flushing."""

    start_time: float = field(default_factory=time.perf_counter)
    counters: dict[str, int] = field(default_factory=dict)
    timers: dict[str, float] = field(default_factory=dict)
    last_flush: float = field(default_factory=time.perf_counter)
    path: Path | None = None

    def inc(self, key: str, value: int = 1) -> None:
        """Increment a counter."""

        self.counters[key] = self.counters.get(key, 0) + value

    def add_time(self, key: str, duration: float) -> None:
        """Record a duration in seconds."""

        self.timers[key] = self.timers.get(key, 0.0) + duration

    def snapshot(self) -> dict:
        """Return a snapshot of current metrics including uptime."""

        uptime = time.perf_counter() - self.start_time
        out = {
            "uptime": uptime,
            "counters": dict(self.counters),
            "timers": dict(self.timers),
        }
        return out


def flush_metrics(state: MetricsState, force: bool = False) -> None:
    """Flush metrics to disk if a path is configured."""

    if state.path is None:
        return
    now = time.perf_counter()
    if not force and now - state.last_flush < 1.0:
        return
    state.last_flush = now
    snap = state.snapshot()
    logger.info("metrics_flush", extra={"metrics": snap})
    with state.path.open("a", encoding="utf8") as fh:
        fh.write(json.dumps(snap) + "\n")


__all__ = ["MetricsState", "flush_metrics"]
