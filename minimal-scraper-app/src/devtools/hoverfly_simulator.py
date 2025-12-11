# file: src/devtools/hoverfly_simulator.py
"""
Stub for Hoverfly-based HTTP simulation.

This can be wired later to record / replay HTTP traffic for scrapers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


def export_simulation(path: str | Path) -> None:
    """
    Placeholder: write an empty simulation file.
    """
    path = Path(path)
    path.write_text("{}", encoding="utf-8")


def import_simulation(path: str | Path) -> Dict[str, Any]:
    """
    Placeholder: read a simulation file and return its parsed dict.
    """
    import json

    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
