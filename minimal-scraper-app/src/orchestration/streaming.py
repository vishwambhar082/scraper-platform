"""
Streaming orchestrator that reacts to events (e.g., Kafka messages).
"""
from __future__ import annotations

from typing import Callable, Dict, Iterable

from src.entrypoints.run_pipeline import run_pipeline


class StreamingOrchestrator:
    def __init__(self, event_source: Iterable[Dict[str, object]]) -> None:
        self.event_source = event_source

    def consume(self, callback: Callable[[Dict[str, object], Dict[str, object]], None]) -> None:
        for event in self.event_source:
            source = event.get("source")
            if not source:
                continue
            result = run_pipeline(
                source=str(source),
                run_type=str(event.get("run_type", "DELTA")),
                environment=str(event.get("environment", "prod")),
                params=event.get("params") or {},
            )
            callback(event, result)

