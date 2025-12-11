# src/observability/source_health_api.py

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

from src.common.paths import OUTPUT_DIR
from src.common.logging_utils import get_logger
from src.observability.session_health import summarize_session_health
from src.observability.cost_tracking import latest_cost_for_source, iter_cost_records_from_db
from src.observability.metrics import dump_metrics, set_gauge

log = get_logger("source-health")


@dataclass
class SourceHealth:
    source: str
    last_run_at: Optional[str]
    last_output_file: Optional[str]
    last_output_rows: int
    session_summary: Dict[str, int]
    last_cost_usd: Optional[float]


def _latest_output_file(source: str) -> Optional[Path]:
    base = OUTPUT_DIR / source / "daily"
    if not base.exists():
        return None
    files = sorted(base.glob("*.csv"))
    return files[-1] if files else None


def _count_rows(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            return max(0, sum(1 for _ in reader) - 1)  # minus header
    except (OSError, csv.Error, UnicodeDecodeError) as exc:
        log.warning("Failed to count rows in %s: %s", path, exc)
        return 0
    except Exception as exc:
        log.warning("Unexpected error counting rows in %s: %s", path, exc)
        return 0


def get_source_health(source: str) -> SourceHealth:
    last_file = _latest_output_file(source)
    last_run_at = None
    last_rows = 0
    if last_file is not None:
        mtime = datetime.utcfromtimestamp(last_file.stat().st_mtime)
        last_run_at = mtime.isoformat()
        last_rows = _count_rows(last_file)

    sess_summary = summarize_session_health(source)
    cost = _latest_cost(source)
    last_cost_usd = cost.get("total_usd") if cost else None
    _record_observability_metrics(source, last_rows, last_cost_usd)

    return SourceHealth(
        source=source,
        last_run_at=last_run_at,
        last_output_file=str(last_file) if last_file else None,
        last_output_rows=last_rows,
        session_summary=sess_summary,
        last_cost_usd=last_cost_usd,
    )


def _latest_cost(source: str) -> Optional[Dict[str, object]]:
    """Return latest cost with DB first, JSONL fallback."""

    db_records = [r for r in iter_cost_records_from_db() if r.get("source") == source]
    if db_records:
        return db_records[-1]
    return latest_cost_for_source(source)


def _record_observability_metrics(source: str, rows: int, cost_usd: Optional[float]) -> None:
    set_gauge("last_output_rows", rows, source=source)
    if cost_usd is not None:
        set_gauge("last_run_cost_usd", cost_usd, source=source)
    # Ensure snapshots reflect latest values for offline dashboards.
    dump_metrics()




__all__ = ["SourceHealth", "get_source_health"]
