"""
Simple circuit breaker implementation.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, TypeVar

T = TypeVar("T")


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    reset_timeout: float = 60.0

    def __post_init__(self) -> None:
        self._failure_count = 0
        self._opened_at = 0.0

    def _is_open(self) -> bool:
        if self._failure_count < self.failure_threshold:
            return False
        if (time.time() - self._opened_at) > self.reset_timeout:
            self._failure_count = 0
            return False
        return True

    def call(self, func: Callable[[], T]) -> T:
        if self._is_open():
            raise RuntimeError("Circuit breaker open")

        try:
            result = func()
            self._failure_count = 0
            return result
        except Exception:
            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                self._opened_at = time.time()
            raise

