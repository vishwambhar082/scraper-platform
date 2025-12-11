from __future__ import annotations

from typing import List, Dict, Any
import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def export_to_csv(path: str | Path, records: List[Dict[str, Any]]) -> str:
    if not records:
        logger.info("export_to_csv: no records")
        return str(path)

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted(records[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    logger.info("export_to_csv: wrote %s records to %s", len(records), path)
    return str(path)


__all__ = ["export_to_csv"]
