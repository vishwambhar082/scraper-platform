"""
Retry helper with exponential backoff.
"""
from __future__ import annotations

import random
import time
from typing import Any, Callable, Iterable, Type, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def retry(
    *,
    attempts: int = 3,
    backoff: float = 1.0,
    jitter: float = 0.1,
    exceptions: Iterable[Type[BaseException]] = (Exception,),
) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        def wrapper(*args: Any, **kwargs: Any):
            last_exc: BaseException | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:  # type: ignore[arg-type]
                    last_exc = exc
                    if attempt == attempts:
                        raise
                    sleep_for = backoff * (2 ** (attempt - 1))
                    sleep_for += random.uniform(-jitter, jitter)
                    time.sleep(max(0.0, sleep_for))
            if last_exc:
                raise last_exc
        return wrapper  # type: ignore[return-value]

    return decorator

