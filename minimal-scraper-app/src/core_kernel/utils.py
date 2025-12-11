# file: src/core_kernel/utils.py
"""
Assorted helpers used across the core_kernel package.
Kept tiny on purpose, to avoid circular imports.
"""

from __future__ import annotations

from typing import Iterable, List, TypeVar

T = TypeVar("T")


def chunked(iterable: Iterable[T], size: int) -> List[List[T]]:
    """
    Split an iterable into chunks of at most `size`.
    Useful for batch DB writes, bulk exports, etc.
    """
    buf: List[T] = []
    out: List[List[T]] = []
    for item in iterable:
        buf.append(item)
        if len(buf) >= size:
            out.append(buf)
            buf = []
    if buf:
        out.append(buf)
    return out
