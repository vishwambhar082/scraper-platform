# file: src/processors/exporters/json_exporter.py
"""
JSON export helper.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Mapping


def export_to_json(
    records: Iterable[Mapping[str, object]],
    path: str | Path,
    indent: int = 2,
) -> None:
    """
    Dump records into a JSON file as a list.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(list(records), f, ensure_ascii=False, indent=indent)
