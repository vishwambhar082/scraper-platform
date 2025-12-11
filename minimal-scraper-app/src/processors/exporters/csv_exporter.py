# file: src/processors/exporters/csv_exporter.py
"""
CSV export helper.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Mapping


def export_to_csv(
    records: Iterable[Mapping[str, object]],
    path: str | Path,
) -> None:
    """
    Write records to a CSV file. Assumes all dicts share the same keys.
    """
    records = list(records)
    if not records:
        return

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(records[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in records:
            writer.writerow(row)
