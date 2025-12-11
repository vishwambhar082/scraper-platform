"""Flag catalog and helpers for OpenFeature-style evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, List, Mapping

from src.governance.rollout_strategies import FlagStrategy, PercentageRollout


@dataclass
class FeatureFlag:
    """Representation of a feature flag and its rollout configuration."""

    key: str
    default: bool = False
    description: str | None = None
    strategies: List[FlagStrategy] = field(default_factory=list)

    def evaluate(self, context: Mapping[str, Any] | None = None) -> bool:
        for strategy in self.strategies:
            result = strategy.evaluate(context)
            if result is not None:
                return bool(result)
        return bool(self.default)


# Centralized catalog of known flags so tests and runtime can share semantics.
_FEATURES: Iterable[FeatureFlag] = (
    FeatureFlag(
        key="pcid.vector_store.similarity_fallback",
        default=True,
        description="Allow cosine-similarity fallback when no exact PCID index hit exists.",
    ),
    FeatureFlag(
        key="pcid.vector_store.remote_backend",
        default=True,
        description="Allow connecting to a remote vector-store backend when configured.",
    ),
    FeatureFlag(
        key="agents.selector_patch.rollout",
        default=False,
        strategies=[PercentageRollout(percentage=15.0)],
        description="Gradually enable automatic selector patching via DeepAgent.",
    ),
    FeatureFlag(
        key="governance.force_local_replay",
        default=False,
        description="Force replay using locally cached responses for validation runs.",
    ),
)


FEATURE_FLAGS: Mapping[str, FeatureFlag] = {flag.key: flag for flag in _FEATURES}
