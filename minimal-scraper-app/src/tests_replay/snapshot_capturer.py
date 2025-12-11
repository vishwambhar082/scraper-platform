# src/tests_replay/snapshot_capturer.py
from __future__ import annotations

from pathlib import Path

from src.common.logging_utils import get_logger
from src.common.paths import REPLAY_SNAPSHOTS_DIR

log = get_logger("snapshot-capturer")


def save_snapshot(source: str, kind: str, name: str, html: str) -> Path:
    base = REPLAY_SNAPSHOTS_DIR / source / kind
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{name}.html"
    path.write_text(html, encoding="utf-8")
    log.debug("Saved snapshot for %s/%s: %s", source, kind, path)
    return path
