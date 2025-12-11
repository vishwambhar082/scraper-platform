from __future__ import annotations

import os
from typing import Dict, Optional, Any

from src.common.logging_utils import get_logger

log = get_logger("prometheus-exporter")

try:
    from prometheus_client import (
        start_http_server,
        Counter,
        Gauge,
        CollectorRegistry as PromCollectorRegistry,
        generate_latest,
    )  # type: ignore[import]
except Exception:  # pragma: no cover
    start_http_server = None  # type: ignore[assignment]
    Counter = Gauge = None  # type: ignore[assignment]
    PromCollectorRegistry = None  # type: ignore[assignment]
    generate_latest = None  # type: ignore[assignment]


class _StubCollectorRegistry:
    """Lightweight stand-in when prometheus_client is unavailable."""

    def __init__(self) -> None:
        self._metrics: list[Any] = []

    def register(self, metric: Any) -> None:
        self._metrics.append(metric)


CollectorRegistry = PromCollectorRegistry or _StubCollectorRegistry


class _NoopCounter:
    """Minimal counter shim that tracks increments without Prometheus."""

    def __init__(self) -> None:
        self.value = 0

    def inc(self, amount: float = 1.0) -> None:
        self.value += amount

    def labels(self, **_: Any) -> "_NoopCounter":
        return self


PROMETHEUS_AVAILABLE = Counter is not None and CollectorRegistry is not _StubCollectorRegistry


SCRAPER_RUNS = None
SCRAPER_ERRORS = None


def init_metrics() -> None:
    """
    Initialise Prometheus metrics if PROMETHEUS_ENABLED=1 and
    prometheus_client is installed. Idempotent.
    """
    global SCRAPER_RUNS, SCRAPER_ERRORS

    if os.getenv("PROMETHEUS_ENABLED", "0") != "1":
        log.info("Prometheus metrics disabled (PROMETHEUS_ENABLED != 1)")
        return

    if start_http_server is None or Counter is None:
        log.warning(
            "prometheus_client not installed; metrics disabled even though "
            "PROMETHEUS_ENABLED=1"
        )
        return

    if SCRAPER_RUNS is not None:
        return  # already initialised

    SCRAPER_RUNS = Counter("scraper_runs_total", "Total scraper runs", ["source"])  # type: ignore[call-arg]
    SCRAPER_ERRORS = Counter("scraper_errors_total", "Total scraper errors", ["source"])  # type: ignore[call-arg]

    port = int(os.getenv("PROMETHEUS_PORT", "9100"))
    start_http_server(port)  # type: ignore[call-arg]
    log.info("Prometheus metrics server started", extra={"port": port})


def record_run(source: str, error: bool = False) -> None:
    if SCRAPER_RUNS is None or SCRAPER_ERRORS is None:
        return
    SCRAPER_RUNS.labels(source=source).inc()  # type: ignore[call-arg]
    if error:
        SCRAPER_ERRORS.labels(source=source).inc()  # type: ignore[call-arg]


def create_metrics(*, registry: Optional[CollectorRegistry] = None) -> Dict[str, Any]:
    """
    Create the counters expected by tests, regardless of prometheus_client availability.
    """
    reg = registry or CollectorRegistry()
    if PROMETHEUS_AVAILABLE and Counter is not None:
        runs_total = Counter(
            "scraper_runs_total",
            "Total scraper runs",
            ["source"],
            registry=reg,  # type: ignore[arg-type]
        )
        runs_failed = Counter(
            "scraper_runs_failed_total",
            "Total failed scraper runs",
            ["source"],
            registry=reg,  # type: ignore[arg-type]
        )
        runs_total = runs_total.labels(source="default")
        runs_failed = runs_failed.labels(source="default")
    else:
        runs_total = _NoopCounter()
        runs_failed = _NoopCounter()

    return {
        "runs_total": runs_total,
        "runs_failed": runs_failed,
        "_registry": reg,
    }


def dump_metrics(metrics: Dict[str, Any]) -> bytes:
    """
    Serialize metrics for scraping; returns empty payload if unsupported.
    """
    if PROMETHEUS_AVAILABLE and generate_latest is not None:
        registry = metrics.get("_registry")
        if registry is None:
            return b""
        try:
            return generate_latest(registry)  # type: ignore[arg-type]
        except Exception:  # pragma: no cover - defensive
            log.exception("Failed to dump Prometheus metrics")
            return b""
    return b""
