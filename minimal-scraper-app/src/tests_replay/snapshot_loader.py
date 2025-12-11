# src/tests_replay/snapshot_loader.py
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from src.common.paths import REPLAY_SNAPSHOTS_DIR


def _iter_html_files(base: Path) -> Iterable[Path]:
    return (p for p in base.rglob("*") if p.suffix.lower() in {".html", ".htm"})


def list_snapshots(source: str, kind: str | None = None) -> List[Path]:
    """Return all HTML snapshots for a source, optionally filtering by kind.

    When ``kind`` is not provided, the search recurses across all nested
    directories beneath ``REPLAY_SNAPSHOTS_DIR / source`` so that grouped
    snapshots (e.g., daily/weekly) are returned in a single listing.
    """

    base = REPLAY_SNAPSHOTS_DIR / source
    if kind:
        base = base / kind
    if not base.exists():
        return []
    return sorted(_iter_html_files(base))
