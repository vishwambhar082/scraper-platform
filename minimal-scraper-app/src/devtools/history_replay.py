"""Utilities for replaying scraper step histories for debugging."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List


@dataclass
class HistoryEvent:
    step: str
    payload: str


class HistoryReplay:
    def __init__(self, history: Iterable[HistoryEvent]) -> None:
        self.history: List[HistoryEvent] = list(history)

    def render_trace(self) -> str:
        return "\n".join(f"[{event.step}] {event.payload}" for event in self.history)

    def search(self, term: str) -> List[HistoryEvent]:
        term_lower = term.lower()
        return [event for event in self.history if term_lower in event.payload.lower()]
