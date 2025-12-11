from __future__ import annotations

from typing import Any
import logging

from .http_engine import HttpEngine
from .playwright_engine import PlaywrightEngine
from .selenium_engine import SeleniumEngine

logger = logging.getLogger(__name__)


def build_engine(engine_type: str, **kwargs: Any):
    """Return an engine instance based on engine_type."""

    engine_type = engine_type.lower()
    if engine_type == "http":
        return HttpEngine(**kwargs)
    if engine_type == "playwright":
        return PlaywrightEngine(**kwargs)
    if engine_type == "selenium":
        return SeleniumEngine(**kwargs)
    raise ValueError(f"Unsupported engine_type: {engine_type}")


__all__ = ["build_engine"]
