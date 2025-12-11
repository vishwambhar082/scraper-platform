# src/observability/tracing.py
from __future__ import annotations
from contextlib import contextmanager
from typing import Iterator, Optional
from src.common.logging_utils import get_logger

log = get_logger("tracing")

try:
    from opentelemetry import trace  # type: ignore[import]
except Exception:  # noqa: BLE001
    trace = None  # type: ignore[assignment]

@contextmanager
def span(name: str, attributes: Optional[dict] = None) -> Iterator[None]:
    if trace is None:
        log.debug("span(start): %s %s", name, attributes or {})
        try:
            yield
        finally:
            log.debug("span(end): %s", name)
        return
    tracer = trace.get_tracer("scraper-platform")
    with tracer.start_as_current_span(name) as s:  # type: ignore[union-attr]
        if attributes:
            for k, v in attributes.items():
                try:
                    s.set_attribute(k, v)  # type: ignore[union-attr]
                except Exception:
                    pass
        yield
