"""
Simple in-memory work queue abstraction.
"""
from __future__ import annotations

from collections import deque
from typing import Deque, Generic, Iterable, Iterator, TypeVar

T = TypeVar("T")


class WorkQueue(Generic[T]):
    def __init__(self, items: Iterable[T] | None = None) -> None:
        self._queue: Deque[T] = deque(items or [])

    def push(self, item: T) -> None:
        self._queue.append(item)

    def pop(self) -> T:
        return self._queue.popleft()

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._queue)

    def __iter__(self) -> Iterator[T]:
        while self._queue:
            yield self.pop()

