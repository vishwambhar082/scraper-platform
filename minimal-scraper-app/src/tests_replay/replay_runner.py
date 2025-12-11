# src/tests_replay/replay_runner.py

from __future__ import annotations

import argparse
from pathlib import Path
import re

from src.common.paths import REPLAY_SNAPSHOTS_DIR
from src.common.logging_utils import get_logger
from src.tests_replay.history_replay import replay_history
from src.tests_replay.snapshot_loader import list_snapshots

log = get_logger("replay-runner")


def _extract_title(html: str) -> str:
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except ModuleNotFoundError:
        match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if not match:
            return "<no title>"
        return match.group(1).strip() or "<no title>"

    soup = BeautifulSoup(html, "html.parser")
    return (soup.title.string.strip() if soup.title and soup.title.string else "") or "<no title>"


def describe_snapshot(path: Path) -> None:
    try:
        html = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        log.warning("Failed to read snapshot %s: %s", path, exc)
        return

    try:
        display_name = str(path.relative_to(REPLAY_SNAPSHOTS_DIR))
    except ValueError:
        display_name = path.name

    title = _extract_title(html)
    log.info("Snapshot %s — title=%r", display_name, title)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Replay snapshot inspector")
    parser.add_argument("source", help="Source name (e.g., alfabeta)")
    parser.add_argument("--kind", help="Optional scraper kind (e.g., daily, weekly)")
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Show diffs between sequential snapshots to highlight drift",
    )
    parser.add_argument(
        "--context",
        type=int,
        default=3,
        help="Number of context lines to include in unified diff output",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    snaps = list_snapshots(args.source, args.kind)
    if not snaps:
        extra = f", kind={args.kind}" if args.kind else ""
        print(f"No snapshots found for source={args.source}{extra} under {REPLAY_SNAPSHOTS_DIR}")
        return

    extra = f"/kind={args.kind}" if args.kind else ""
    print(f"Found {len(snaps)} snapshots for source={args.source}{extra}")
    for p in snaps:
        describe_snapshot(p)

    if args.diff:
        print("\n=== Drift and diff report ===")
        results = replay_history(args.source, args.kind, diff_context=args.context)
        for res in results:
            drift_flag = " (schema drift)" if res.schema_drift else ""
            previous = res.previous.name if res.previous else "<none>"
            print(f"- {res.name}: prev={previous}, signature={res.schema_signature}{drift_flag}")
            if res.diff:
                print(res.diff.rstrip())


if __name__ == "__main__":
    main()
