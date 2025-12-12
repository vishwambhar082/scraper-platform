"""Helpers to evaluate policy constraints for scraper components."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Set

from .vault_client import VaultClient


@dataclass
class PolicyDecision:
    allowed: bool
    missing: Set[str]


class PolicyGuard:
    """Runs capability checks against Vault policies."""

    def __init__(self, vault: VaultClient) -> None:
        self.vault = vault

    def check(self, policy_name: str, required_capabilities: Iterable[str]) -> PolicyDecision:
        policy = self.vault.load_policy(policy_name)
        available = set(policy.get("capabilities", []))
        required = set(required_capabilities)
        missing = required - available
        return PolicyDecision(allowed=len(missing) == 0, missing=missing)

    def require(self, policy_name: str, required_capabilities: Iterable[str]) -> None:
        decision = self.check(policy_name, required_capabilities)
        if not decision.allowed:
            missing = ", ".join(sorted(decision.missing))
            raise PermissionError(f"Policy '{policy_name}' is missing required capabilities: {missing}")

    def evaluate_source_access(self, policy_map: Mapping[str, Iterable[str]]) -> Mapping[str, PolicyDecision]:
        return {name: self.check(name, caps) for name, caps in policy_map.items()}
