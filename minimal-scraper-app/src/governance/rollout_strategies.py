"""Reusable rollout strategies for feature-flag evaluation.

These helpers model common OpenFeature-like rollout behaviours such as
percentage-based bucketing and environment targeting. Strategies can be
combined on a :class:`~src.governance.openfeature_flags.FeatureFlag` to express
progressive delivery rules without an external provider.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping, Optional


class FlagStrategy:
    """Base class for a rollout strategy.

    Subclasses return ``True``/``False`` to explicitly enable/disable a flag,
    or ``None`` when the strategy cannot make a decision (e.g. missing context).
    """

    def evaluate(self, context: Mapping[str, Any] | None = None) -> Optional[bool]:
        raise NotImplementedError


@dataclass
class PercentageRollout(FlagStrategy):
    """Gradually enable a flag for a percentage of actors.

    A stable bucket is computed from a deterministic attribute (``actor_id`` by
    default) so that the same actor deterministically lands in the same bucket
    across evaluations.
    """

    percentage: float
    bucket_by: str = "actor_id"

    def evaluate(self, context: Mapping[str, Any] | None = None) -> Optional[bool]:
        if context is None:
            return None

        actor = context.get(self.bucket_by)
        if actor is None:
            return None

        # Compute a stable 0-99 bucket using a hash of the actor identifier.
        digest = hashlib.md5(str(actor).encode("utf-8"))  # noqa: S324 - non-crypto hash for bucketing
        bucket = int(digest.hexdigest(), 16) % 100
        return bucket < self.percentage


@dataclass
class EnvironmentMatchStrategy(FlagStrategy):
    """Toggle a flag only for specific runtime environments."""

    allowed: tuple[str, ...]
    context_key: str = "env"

    def evaluate(self, context: Mapping[str, Any] | None = None) -> Optional[bool]:
        if context is None:
            return None

        env_value = context.get(self.context_key)
        if env_value is None:
            return None

        return str(env_value) in self.allowed


@dataclass
class AttributeEqualsStrategy(FlagStrategy):
    """Enable a flag when a context attribute matches the expected value."""

    key: str
    expected_value: Any

    def evaluate(self, context: Mapping[str, Any] | None = None) -> Optional[bool]:
        if context is None:
            return None

        if self.key not in context:
            return None

        return context.get(self.key) == self.expected_value
