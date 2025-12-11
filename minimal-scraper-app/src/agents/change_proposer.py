# file: src/agents/change_proposer.py
"""
High-level wrapper around patch_proposer.

Used by DeepAgents to suggest scraper changes.
"""

from __future__ import annotations

from typing import Any, Dict

from src.agents import patch_proposer


def propose_changes(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a proposed patch based on a snapshot / failure context.
    """
    return patch_proposer.propose_patch(snapshot)
