"""
Engine selection helpers and unified engine interface.

This module provides a thin abstraction so scrapers can choose
which engine to use (selenium / http / playwright / groq_browser) based on the
per-source config, instead of hardcoding selenium everywhere.
"""

from __future__ import annotations

import importlib
from typing import Any, Mapping, Literal, TYPE_CHECKING, Callable

from .base_engine import BaseEngine, EngineConfig, EngineError, EngineResult, RateLimitError
from .engine_factory import create_engine
from .rate_limiter import SimpleRateLimiter

if TYPE_CHECKING:
    from .http_client import HttpRequestConfig


EngineType = Literal["selenium", "http", "playwright", "groq_browser"]


def _normalize_engine_type(raw: str | None) -> EngineType:
    if not raw:
        return "selenium"
    raw = raw.strip().lower()
    if raw in ("http", "requests", "rest"):
        return "http"
    if raw in ("playwright", "pw"):
        return "playwright"
    if raw in ("groq", "groq_browser", "groq-browser", "browserbase"):
        return "groq_browser"
    # default fallback for anything unknown
    return "selenium"


def get_engine_type_for_source(source_config: Mapping[str, Any]) -> EngineType:
    """
    Read engine type from config for a given source.

    Expects config structure like:

        engine:
          type: selenium | http | playwright
    """
    engine_cfg = source_config.get("engine") or {}
    return _normalize_engine_type(engine_cfg.get("type"))


def build_rate_limiter_from_config(global_config: Mapping[str, Any]) -> SimpleRateLimiter | None:
    """
    Optional helper: build a SimpleRateLimiter from config/settings.yaml.

    Expected structure:

        scraping:
          default_rate_limit:
            min_delay: 0.5
            max_delay: 2.0
    """
    scraping_cfg = global_config.get("scraping") or {}
    rl_cfg = scraping_cfg.get("default_rate_limit") or {}
    min_delay = rl_cfg.get("min_delay")
    max_delay = rl_cfg.get("max_delay")

    if min_delay is None or max_delay is None:
        return None

    return SimpleRateLimiter(min_delay=float(min_delay), max_delay=float(max_delay))


def _import_engine_module(module: str, dependency_hint: str | None = None):
    """
    Import an engine submodule lazily so optional deps don't break imports.
    """
    try:
        return importlib.import_module(f".{module}", __package__)
    except ModuleNotFoundError as exc:
        if dependency_hint and exc.name == dependency_hint:
            raise RuntimeError(
                f"The {module} requires the '{dependency_hint}' package. "
                f"Install it or disable that engine."
            ) from exc
        raise


def get_http_engine() -> tuple[Callable[..., Any], "HttpRequestConfig"]:
    """
    Convenience wrapper so callers don’t import http_client directly.

    Returns:
        (send_request_function, HttpRequestConfig_class)
    """
    http_client = _import_engine_module("http_client")
    return http_client.send_request, http_client.HttpRequestConfig


def get_selenium_engine():
    """
    Convenience wrapper to access selenium helpers in a single place.
    """
    return _import_engine_module("selenium_engine", dependency_hint="selenium")


def get_playwright_engine():
    """
    Convenience wrapper for playwright helpers.
    """
    return _import_engine_module("playwright_engine", dependency_hint="playwright")


def get_groq_browser_engine():
    """
    Convenience wrapper for Groq browser automation helpers.
    """
    return _import_engine_module("groq_browser", dependency_hint="groq")


__all__ = [
    "BaseEngine",
    "EngineConfig",
    "EngineError",
    "EngineResult",
    "RateLimitError",
    "create_engine",
    "get_engine_type_for_source",
    "build_rate_limiter_from_config",
    "get_http_engine",
    "get_selenium_engine",
    "get_playwright_engine",
    "get_groq_browser_engine",
]
