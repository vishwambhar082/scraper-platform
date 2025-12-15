"""
Simple weighted round robin load balancer for scraper engines.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Iterable


@dataclass
class Backend:
    name: str
    weight: int = 1


class LoadBalancer:
    def __init__(self, backends: Iterable[Backend]):
        weighted: Deque[str] = deque()
        for backend in backends:
            weighted.extend([backend.name] * max(1, backend.weight))
        if not weighted:
            raise ValueError("Load balancer requires at least one backend")
        self._ring = weighted

    def next_backend(self) -> str:
        backend = self._ring[0]
        self._ring.rotate(-1)
        return backend

