"""
Manages a pool of reusable browser sessions.
"""
from __future__ import annotations

from contextlib import contextmanager
from queue import Queue
from typing import Iterator

from src.common.logging_utils import get_logger

log = get_logger("browser-pool")


class BrowserPool:
    def __init__(self, factory, size: int = 2) -> None:
        self.factory = factory
        self.pool: Queue = Queue(maxsize=size)
        for _ in range(size):
            self.pool.put(self.factory())

    @contextmanager
    def acquire(self) -> Iterator:
        browser = self.pool.get()
        log.debug("Acquired browser session")
        try:
            yield browser
        finally:
            self.pool.put(browser)
            log.debug("Released browser session")

