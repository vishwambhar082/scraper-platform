"""
JSON exporter for pipeline outputs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from src.common.paths import OUTPUT_DIR


class JsonExporter:
    def __init__(self, *, output_root: Path | None = None) -> None:
        self.output_root = output_root or (OUTPUT_DIR / "json")
        self.output_root.mkdir(parents=True, exist_ok=True)

    def export(self, data: Iterable[Any], filename: str) -> Path:
        path = self.output_root / filename
        with path.open("w", encoding="utf-8") as handle:
            json.dump(list(data), handle, ensure_ascii=False, indent=2)
        return path

