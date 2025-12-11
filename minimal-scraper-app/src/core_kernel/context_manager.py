# file: src/core_kernel/context_manager.py
"""
Execution context wrapper for a running scraper pipeline.

This keeps:
- run_id
- source_name
- config snapshot
- arbitrary context bag (for agents, observability, etc.)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class PipelineContext:
    run_id: str
    source_name: str
    config: Dict[str, Any] = field(default_factory=dict)
    extras: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        return self.extras.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.extras[key] = value
