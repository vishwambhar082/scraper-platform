"""Helper to build LangGraph-style workflows without requiring the dependency."""
from __future__ import annotations

from typing import Callable, Dict, List


class LangGraphWorkflow:
    def __init__(self) -> None:
        self.steps: List[Callable[[Dict], Dict]] = []

    def add_step(self, fn: Callable[[Dict], Dict]) -> None:
        self.steps.append(fn)

    def run(self, state: Dict) -> Dict:
        current = dict(state)
        for step in self.steps:
            current.update(step(current))
        return current
