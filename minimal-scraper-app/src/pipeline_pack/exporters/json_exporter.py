from __future__ import annotations

from typing import List, Dict, Any
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def export_to_json(path: str | Path, records: List[Dict[str, Any]]) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    logger.info("export_to_json: wrote %s records to %s", len(records), path)
    return str(path)


__all__ = ["export_to_json"]
