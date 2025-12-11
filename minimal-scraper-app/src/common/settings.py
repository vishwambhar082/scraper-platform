# file: src/common/settings.py
"""
Central place for environment-driven settings, if you decide
not to rely solely on config/env/*.yaml.
"""

from __future__ import annotations

import os

_ENV_KEYS = ("SCRAPER_PLATFORM_ENV", "SCRAPER_ENV", "ENV")


def get_runtime_env(default: str | None = "dev") -> str | None:
    """
    Normalized way to resolve the current runtime environment.

    Checks multiple legacy env var names in a deterministic order, returning
    the first non-empty value.
    """

    for key in _ENV_KEYS:
        value = os.getenv(key)
        if value:
            return value
    return default


def get_env(key: str, default: str | None = None) -> str | None:
    """
    Convenience wrapper around os.environ.get.
    """
    return os.environ.get(key, default)
