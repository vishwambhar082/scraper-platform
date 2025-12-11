# src/tests_replay/history_replay.py
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import Iterable, List

from src.common.logging_utils import get_logger
from src.tests_replay.snapshot_diff import diff_html
from src.tests_replay.snapshot_loader import list_snapshots

log = get_logger("history-replay")


def _html_signature(html: str) -> str:
    """Return a lightweight signature of the HTML structure.

    The signature intentionally ignores attribute ordering and whitespace so that
    DOM drift can be detected without requiring full parsing dependencies.
    """

    if find_spec("bs4"):
        from bs4 import BeautifulSoup  # type: ignore

        tags: Iterable[str] = (el.name or "" for el in BeautifulSoup(html, "html.parser").find_all(True))
    else:
        tags = re.findall(r"<([a-zA-Z0-9]+)[\s/>]", html)

    joined = "|".join(tags)
    return hashlib.sha256(joined.encode("utf-8", errors="ignore")).hexdigest()


@dataclass
class ReplayHistoryResult:
    source: str
    kind: str | None
    name: str
    current: Path
    previous: Path | None
    schema_signature: str
    previous_signature: str | None
    diff: str | None

    @property
    def schema_drift(self) -> bool:
        return bool(self.previous_signature and self.previous_signature != self.schema_signature)


def replay_history(source: str, kind: str | None = None, *, diff_context: int = 3) -> List[ReplayHistoryResult]:
    """Walk a source's snapshots to detect DOM/schema drift and HTML diffs."""

    snapshots = list_snapshots(source, kind)
    if not snapshots:
        log.info("No snapshots found for %s", source)
        return []

    results: List[ReplayHistoryResult] = []
    previous_path: Path | None = None
    previous_sig: str | None = None

    for path in snapshots:
        html = path.read_text(encoding="utf-8", errors="ignore")
        signature = _html_signature(html)
        diff = diff_html(previous_path, path, n=diff_context) if previous_path else None

        results.append(
            ReplayHistoryResult(
                source=source,
                kind=kind,
                name=path.stem,
                current=path,
                previous=previous_path,
                schema_signature=signature,
                previous_signature=previous_sig,
                diff=diff,
            )
        )

        previous_path = path
        previous_sig = signature

    return results
