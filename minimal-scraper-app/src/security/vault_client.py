"""Lightweight Vault client wrapper that can read local policy files and secrets.

This module keeps dependencies minimal while mimicking the interface of a Vault
client. It loads policy manifests from ``config/secrets/vault_policies`` by
default but allows overriding the base directory to make testing simple.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class VaultClient:
    """A minimal file-backed Vault client with policy awareness.

    The class keeps a tiny cache of secrets and policy documents to avoid
    repeated disk I/O during a pipeline run. It intentionally does not perform
    any network calls; callers can swap this object for a real hvac client when
    deploying against HashiCorp Vault.
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = Path(base_dir or "config/secrets")
        self._policy_cache: Dict[str, Dict[str, Any]] = {}
        self._secret_cache: Dict[str, str] = {}

    def policy_path(self, policy_name: str) -> Path:
        return self.base_dir / "vault_policies" / f"{policy_name}.json"

    def load_policy(self, policy_name: str) -> Dict[str, Any]:
        if policy_name in self._policy_cache:
            return self._policy_cache[policy_name]
        path = self.policy_path(policy_name)
        if not path.exists():
            raise FileNotFoundError(f"Policy file not found: {path}")
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        self._policy_cache[policy_name] = data
        return data

    def read_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Resolve a secret value.

        The lookup order is environment variable, file in ``base_dir/values``,
        and finally the provided default. Results are cached to avoid repeated
        lookups in hot paths.
        """

        if key in self._secret_cache:
            return self._secret_cache[key]

        if key in os.environ:
            value = os.environ[key]
        else:
            path = self.base_dir / "values" / key
            value = path.read_text(encoding="utf-8").strip() if path.exists() else default
        if value is not None:
            self._secret_cache[key] = value
        return value

    def assert_allowed(self, policy_name: str, capability: str) -> None:
        policy = self.load_policy(policy_name)
        capabilities = set(policy.get("capabilities", []))
        if capability not in capabilities:
            raise PermissionError(f"Capability '{capability}' not permitted by policy '{policy_name}'")

    def clear_cache(self) -> None:
        self._policy_cache.clear()
        self._secret_cache.clear()
