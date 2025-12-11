# file: src/common/utils.py
"""
Generic helpers that don't belong to any specific domain.
"""

from __future__ import annotations

from typing import Iterable, List, TypeVar

T = TypeVar("T")


def flatten(list_of_lists: Iterable[Iterable[T]]) -> List[T]:
    """
    Flatten an iterable of iterables into a single list.
    """
    out: List[T] = []
    for sub in list_of_lists:
        out.extend(sub)
    return out
