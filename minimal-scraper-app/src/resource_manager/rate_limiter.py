# file: src/resource_manager/rate_limiter.py
"""Resource-level rate limiter façade with per-source settings."""

from __future__ import annotations

import time
import threading
from collections import deque
from contextlib import contextmanager
from typing import Deque, Dict, Optional

from src.common.logging_utils import get_logger, safe_log
from src.observability import metrics
from src.resource_manager.settings import get_rate_limit_settings


log = get_logger("rate-limiter")


class RateLimiter:
    """Simple rate limiter supporting QPS and concurrency caps."""

    def __init__(self, key: str, *, max_qps: Optional[float], max_concurrent: Optional[int]):
        self.key = key
        self.max_qps = max_qps or 0.0
        self.max_concurrent = max_concurrent or 0
        self._timestamps: Deque[float] = deque()
        self._lock = threading.Lock()
        self._sem = threading.Semaphore(self.max_concurrent) if self.max_concurrent else None

    def _acquire_concurrency(self) -> bool:
        if not self._sem:
            return False
        if self._sem.acquire(blocking=False):
            return False
        metrics.incr("rate_limit_hits", source=self.key)
        self._sem.acquire()
        return True

    def _respect_qps(self) -> bool:
        if self.max_qps <= 0:
            return False

        waited = False
        with self._lock:
            now = time.time()
            window_start = now - 1.0
            while self._timestamps and self._timestamps[0] < window_start:
                self._timestamps.popleft()

            if len(self._timestamps) >= self.max_qps:
                sleep_for = self._timestamps[0] + 1.0 - now
                if sleep_for > 0:
                    metrics.incr("rate_limit_hits", source=self.key)
                    waited = True
                    time.sleep(sleep_for)

                now = time.time()
                window_start = now - 1.0
                while self._timestamps and self._timestamps[0] < window_start:
                    self._timestamps.popleft()

            self._timestamps.append(time.time())

        return waited

    def _acquire(self) -> None:
        waited_concurrency = self._acquire_concurrency()
        waited_qps = self._respect_qps()
        if waited_concurrency or waited_qps:
            safe_log(
                log,
                "debug",
                "rate_limit_wait",
                {
                    "source": self.key,
                    "waited_for_concurrency": waited_concurrency,
                    "waited_for_qps": waited_qps,
                },
            )

    def _release(self) -> None:
        if self._sem:
            self._sem.release()

    @contextmanager
    def limit(self):
        """Context manager that enforces QPS and concurrency limits."""

        self._acquire()
        try:
            yield
        finally:
            self._release()

    def wait(self) -> None:
        """Maintain compatibility with SimpleRateLimiter-like interface."""

        with self.limit():
            return None


_default_limiters: Dict[str, RateLimiter] = {}


def get_rate_limiter(key: str) -> RateLimiter:
    """Obtain (or create) a rate limiter keyed by source using config defaults."""

    if key not in _default_limiters:
        settings = get_rate_limit_settings(key)
        _default_limiters[key] = RateLimiter(
            key,
            max_qps=settings.get("max_qps"),
            max_concurrent=settings.get("max_concurrent"),
        )
    return _default_limiters[key]
