# src/tests_replay/snapshot_diff.py
from __future__ import annotations

from difflib import unified_diff
from pathlib import Path
from typing import Iterable


def diff_html(old_path: Path, new_path: Path, n: int = 3) -> str:
    old_lines = old_path.read_text(encoding="utf-8").splitlines(keepends=True)
    new_lines = new_path.read_text(encoding="utf-8").splitlines(keepends=True)
    diff: Iterable[str] = unified_diff(
        old_lines,
        new_lines,
        fromfile=str(old_path),
        tofile=str(new_path),
        n=n,
    )
    return "".join(diff)
