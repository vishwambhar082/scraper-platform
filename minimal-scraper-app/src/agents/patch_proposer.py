# src/agents/patch_proposer.py

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SelectorPatch:
    field_name: str
    old_selector: str
    new_selector: str
    confidence: float


def propose_noop_patch(field_name: str, selector: str) -> SelectorPatch:
    """
    Minimal implementation: returns a "no-op" patch.
    Real implementation would use DOM diffs or DeepAgents.
    """
    return SelectorPatch(
        field_name=field_name,
        old_selector=selector,
        new_selector=selector,
        confidence=1.0,
    )


__all__ = ["SelectorPatch", "propose_noop_patch"]
