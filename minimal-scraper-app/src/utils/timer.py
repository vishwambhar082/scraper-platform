"""
Context manager for timing code blocks.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Callable


@contextmanager
def Timer(callback: Callable[[float], None]):
    start = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start
        callback(duration)

