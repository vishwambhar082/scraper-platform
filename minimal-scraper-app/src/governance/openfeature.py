"""Lightweight feature-flag layer with OpenFeature-style helpers.

This module keeps feature toggles centralized and makes it easy to stub or
override values in tests without pulling in an external provider. Flags can be
overridden via environment variable ``FEATURE_FLAGS`` containing a JSON
object, or by using :func:`override_flags` within a test.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from typing import Any, Dict, Mapping, Optional

from src.governance.openfeature_flags import FEATURE_FLAGS, FeatureFlag


def _load_env_overrides() -> Dict[str, bool]:
    raw = os.getenv("FEATURE_FLAGS")
    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    overrides: Dict[str, bool] = {}
    for key, value in parsed.items():
        overrides[key] = bool(value)
    return overrides


class FeatureFlagClient:
    """Simple in-process feature-flag client with rollout support."""

    def __init__(self, defaults: Optional[Mapping[str, FeatureFlag]] = None):
        self._flags: Dict[str, FeatureFlag] = dict(defaults or {})
        self._manual_overrides: Dict[str, bool] = {}

    def is_enabled(
        self, flag_key: str, default: bool = False, *, context: Mapping[str, Any] | None = None
    ) -> bool:
        env_overrides = _load_env_overrides()
        if flag_key in self._manual_overrides:
            return bool(self._manual_overrides[flag_key])

        if flag_key in env_overrides:
            return bool(env_overrides[flag_key])

        if flag_key in self._flags:
            return bool(self._flags[flag_key].evaluate(context))

        return bool(default)

    def set_overrides(self, overrides: Mapping[str, Any]) -> None:
        for key, value in overrides.items():
            self._manual_overrides[key] = bool(value)

    def clear_overrides(self) -> None:
        self._manual_overrides.clear()


_client = FeatureFlagClient(FEATURE_FLAGS)


def is_enabled(
    flag_key: str, *, default: bool = False, context: Mapping[str, Any] | None = None
) -> bool:
    """Check whether a feature flag is enabled, falling back to defaults.

    Context is optional; when present it can drive rollout strategies defined in
    :mod:`src.governance.rollout_strategies`.
    """

    return _client.is_enabled(flag_key, default=default, context=context)


@contextmanager
def override_flags(overrides: Mapping[str, Any]):
    """Temporarily apply flag overrides within a context."""

    previous = dict(_client._manual_overrides)
    try:
        _client.set_overrides(overrides)
        yield _client
    finally:
        _client.clear_overrides()
        _client.set_overrides(previous)
