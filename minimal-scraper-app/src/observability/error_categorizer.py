# src/observability/error_categorizer.py
from __future__ import annotations

from typing import Tuple, Type


def categorize_error(exc: BaseException) -> Tuple[str, str]:
    etype: Type[BaseException] = type(exc)
    name = etype.__name__.lower()

    if "timeout" in name:
        return "network", "timeout"
    if "connection" in name or "socket" in name:
        return "network", "connection"
    if "http" in name or "status" in name:
        return "remote", "http"
    if "selector" in name or "xpath" in name:
        return "scraper", "selector"
    return "unknown", name
