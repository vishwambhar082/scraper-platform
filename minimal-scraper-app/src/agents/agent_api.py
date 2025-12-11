# file: src/agents/agent_api.py
"""
Public entrypoints for driving DeepAgent workflows.

This is a façade on top of agent_orchestrator and friends.
"""

from __future__ import annotations

from typing import Any, Dict

from src.agents import agent_orchestrator


def run_auto_heal(run_id: str, source_name: str, *, dry_run: bool = True) -> Dict[str, Any]:
    """
    Trigger an auto-heal workflow for a given run_id + source.
    """
    return agent_orchestrator.run_auto_heal(run_id=run_id, source_name=source_name, dry_run=dry_run)
