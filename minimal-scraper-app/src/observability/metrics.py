# src/observability/metrics.py

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from threading import Lock
from typing import Dict, Tuple, Any, List
import json
import time
from pathlib import Path

from src.common.logging_utils import get_logger
from src.common.paths import LOGS_DIR


log = get_logger(__name__)


@dataclass
class MetricSample:
    name: str
    labels: Dict[str, Any]
    value: float


class MetricsRegistry:
    def __init__(self) -> None:
        self._counters: Dict[
            Tuple[str, Tuple[Tuple[str, Any], ...]], Tuple[float, float]
        ] = defaultdict(lambda: (0.0, 0.0))
        self._gauges: Dict[Tuple[str, Tuple[Tuple[str, Any], ...]], Tuple[float, float]] = {}
        self._lock = Lock()

    def incr(self, name: str, amount: float = 1.0, **labels: Any) -> None:
        key = (name, tuple(sorted(labels.items())))
        with self._lock:
            current, _ts = self._counters[key]
            self._counters[key] = (current + amount, time.time())

    def set_gauge(self, name: str, value: float, **labels: Any) -> None:
        key = (name, tuple(sorted(labels.items())))
        with self._lock:
            self._gauges[key] = (value, time.time())

    def snapshot(self) -> Dict[str, List[MetricSample]]:
        with self._lock:
            counters = [
                MetricSample(name=k[0], labels=dict(k[1]), value=v)
                for k, (v, _ts) in self._counters.items()
            ]
            gauges = [
                MetricSample(name=k[0], labels=dict(k[1]), value=v)
                for k, (v, _ts) in self._gauges.items()
            ]
        return {"counters": counters, "gauges": gauges}

    def cleanup_expired(self, ttl_seconds: int = 3600) -> int:
        """
        Remove metric series that haven't been updated within `ttl_seconds`.

        Returns the number of removed series.
        """

        now = time.time()
        removed = 0
        with self._lock:
            for key, (_val, ts) in list(self._counters.items()):
                if (now - ts) > ttl_seconds:
                    del self._counters[key]
                    removed += 1

            for key, (_val, ts) in list(self._gauges.items()):
                if (now - ts) > ttl_seconds:
                    del self._gauges[key]
                    removed += 1

        return removed


_registry = MetricsRegistry()


def incr(name: str, amount: float = 1.0, **labels: Any) -> None:
    _registry.incr(name, amount, **labels)


def set_gauge(name: str, value: float, **labels: Any) -> None:
    _registry.set_gauge(name, value, **labels)


def dump_metrics() -> Dict[str, List[MetricSample]]:
    return _registry.snapshot()


def persist_snapshot(path: Path | None = None) -> Path:
    """Persist current metrics to a JSON file for dashboards or audits."""

    path = path or (LOGS_DIR / "metrics_snapshot.json")
    snapshot = dump_metrics()
    serializable = {
        "counters": [s.__dict__ for s in snapshot["counters"]],
        "gauges": [s.__dict__ for s in snapshot["gauges"]],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2)
    return path


def cleanup_expired_metrics(ttl_seconds: int = 3600) -> int:
    """
    Remove metric series that haven't been updated within `ttl_seconds`.

    Call this periodically from a maintenance task, e.g. once per minute.
    """

    removed = _registry.cleanup_expired(ttl_seconds)
    if removed:
        log.info(
            "metrics_cleanup",
            extra={"removed_series": removed, "ttl_seconds": ttl_seconds},
        )
    return removed


__all__ = [
    "incr",
    "set_gauge",
    "dump_metrics",
    "persist_snapshot",
    "cleanup_expired_metrics",
    "MetricSample",
    "MetricsRegistry",
]
