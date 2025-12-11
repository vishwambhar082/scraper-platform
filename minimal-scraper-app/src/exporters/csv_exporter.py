"""
CSV exporter for pipeline outputs.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from src.common.paths import OUTPUT_DIR


class CsvExporter:
    def __init__(self, *, output_root: Path | None = None) -> None:
        self.output_root = output_root or (OUTPUT_DIR / "csv")
        self.output_root.mkdir(parents=True, exist_ok=True)

    def export(self, records: Iterable[Mapping[str, object]], filename: str) -> Path:
        path = self.output_root / filename
        records = list(records)
        if not records:
            raise ValueError("CSV exporter requires at least one record")

        fieldnames: Sequence[str] = list(records[0].keys())
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
        return path

