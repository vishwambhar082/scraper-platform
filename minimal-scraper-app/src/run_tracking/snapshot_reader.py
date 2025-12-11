# file: src/run_tracking/snapshot_reader.py
"""
Helpers to read snapshot artifacts written during pipeline execution.

This is meant to be used by replay tools and DeepAgents.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


def load_snapshot(path: str | Path) -> Dict[str, Any]:
    """
    Load a JSON snapshot from disk.

    The exact format is intentionally left flexible; adjust as needed.
    """
    import json

    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
