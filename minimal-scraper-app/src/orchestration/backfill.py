"""
Backfill coordinator that replays historical windows.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, Iterable, List

from src.entrypoints.run_pipeline import run_pipeline


class BackfillCoordinator:
    def __init__(self, source: str) -> None:
        self.source = source

    def run_backfill(self, start: date, end: date) -> List[Dict[str, object]]:
        current = start
        results: List[Dict[str, object]] = []
        while current <= end:
            params = {"as_of_date": current.isoformat()}
            results.append(
                run_pipeline(
                    source=self.source,
                    run_type="BACKFILL",
                    params=params,
                    environment="prod",
                )
            )
            current += timedelta(days=1)
        return results

