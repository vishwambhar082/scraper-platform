"""
High-level rate limit enforcement facade that wraps resource manager primitives.
"""
from __future__ import annotations

from contextlib import contextmanager

from src.resource_manager.rate_limiter import get_rate_limiter


class RateLimitEnforcer:
    def __init__(self, source: str) -> None:
        self.source = source
        self._limiter = get_rate_limiter(source)

    @contextmanager
    def limit(self):
        with self._limiter.limit():
            yield

    def wait(self) -> None:
        self._limiter.wait()

