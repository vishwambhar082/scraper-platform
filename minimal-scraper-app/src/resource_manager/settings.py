from __future__ import annotations

"""Helpers for loading per-source resource manager settings."""

from functools import lru_cache
from typing import Any, Dict

from src.common.config_loader import load_source_config
from src.common.logging_utils import get_logger, safe_log

log = get_logger("resource-settings")

DEFAULT_RATE_LIMITS: Dict[str, Any] = {"max_qps": None, "max_concurrent": None}
DEFAULT_PROXY_SETTINGS: Dict[str, Any] = {
    "max_errors_before_ban": 3,
    "ban_window_minutes": 30,
}


@lru_cache(maxsize=64)
def get_source_config(source: str) -> Dict[str, Any]:
    """Load and cache a source configuration for downstream helpers."""

    try:
        return load_source_config(source)
    except Exception as exc:  # noqa: BLE001
        safe_log(
            log,
            "warning",
            "Failed to load source config; using defaults",
            {"source": source, "error": str(exc)},
        )
        return {}


def get_rate_limit_settings(source: str) -> Dict[str, Any]:
    """Return rate limit settings merged with defaults for a source."""

    settings = dict(DEFAULT_RATE_LIMITS)
    settings.update(get_source_config(source).get("rate_limits", {}) or {})
    return settings


def get_proxy_settings(source: str) -> Dict[str, Any]:
    """Return proxy settings merged with defaults for a source."""

    settings = dict(DEFAULT_PROXY_SETTINGS)
    settings.update(get_source_config(source).get("proxies", {}) or {})
    return settings


__all__ = ["get_rate_limit_settings", "get_proxy_settings", "get_source_config"]
