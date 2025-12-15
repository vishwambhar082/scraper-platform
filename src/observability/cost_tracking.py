# src/observability/cost_tracking.py

from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

from src.common.paths import LOGS_DIR
from src.common.logging_utils import get_logger

log = get_logger("cost-tracking")

COST_LOG_PATH: Path = LOGS_DIR / "cost_runs.jsonl"
COST_DB_PATH: Path = LOGS_DIR / "cost_runs.db"


@dataclass
class CostRecord:
    run_id: str
    source: str
    proxy_cost_usd: float = 0.0
    compute_cost_usd: float = 0.0
    other_cost_usd: float = 0.0
    currency: str = "USD"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def total_usd(self) -> float:
        return self.proxy_cost_usd + self.compute_cost_usd + self.other_cost_usd


def record_run_cost(
    source: str,
    run_id: str,
    proxy_cost_usd: float = 0.0,
    compute_cost_usd: float = 0.0,
    other_cost_usd: float = 0.0,
    currency: str = "USD",
) -> CostRecord:
    rec = CostRecord(
        run_id=run_id,
        source=source,
        proxy_cost_usd=proxy_cost_usd,
        compute_cost_usd=compute_cost_usd,
        other_cost_usd=other_cost_usd,
        currency=currency,
    )
    payload: Dict[str, Any] = asdict(rec)
    payload["total_usd"] = rec.total_usd
    try:
        _persist_cost_record(payload)
    except Exception:  # pragma: no cover - defensive guard
        log.exception("Failed to persist cost record")
        raise

    log.info("Recorded cost for run %s (%s): total_usd=%.4f", rec.run_id, rec.source, rec.total_usd)
    return rec


def _persist_cost_record(payload: Dict[str, Any]) -> None:
    """Persist cost record to PostgreSQL and file log."""
    import os
    from src.common.db import transaction
    from src.observability.run_trace_context import get_current_tenant_id

    COST_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Write to file log (always, for backup)
    try:
        with COST_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception as e:
        log.warning("Failed to write cost record to file log: %s", e)

    # Write to PostgreSQL (primary storage)
    db_url = os.getenv("DB_URL")
    if not db_url:
        log.debug("DB_URL not configured; cost record logged to file only")
        return

    try:
        tenant_id = get_current_tenant_id() or "default"
        with transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO scraper.cost_tracking (
                    source, run_id, proxy_cost_usd, compute_cost_usd, other_cost_usd,
                    currency, tenant_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    payload["source"],
                    payload["run_id"],
                    payload["proxy_cost_usd"],
                    payload["compute_cost_usd"],
                    payload["other_cost_usd"],
                    payload["currency"],
                    tenant_id,
                ),
            )
            conn.commit()
            log.debug("Cost record persisted to PostgreSQL: %s/%s", payload["source"], payload["run_id"])
    except Exception as e:
        log.warning("Failed to persist cost record to PostgreSQL (file log succeeded): %s", e)
        # Don't raise - file log is sufficient fallback


def iter_cost_records() -> List[Dict[str, Any]]:
    if not COST_LOG_PATH.exists():
        return []
    records: List[Dict[str, Any]] = []
    with COST_LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                log.warning("Skipping malformed cost log line: %r", line[:200])
    return records


def iter_cost_records_from_db() -> List[Dict[str, Any]]:
    """Read cost records from PostgreSQL."""
    import os
    from src.common.db import get_conn

    db_url = os.getenv("DB_URL")
    if not db_url:
        log.debug("DB_URL not configured; falling back to file log")
        return iter_cost_records()

    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT source, run_id, proxy_cost_usd, compute_cost_usd, other_cost_usd,
                   currency, created_at,
                   (proxy_cost_usd + compute_cost_usd + other_cost_usd) as total_usd
            FROM scraper.cost_tracking
            ORDER BY created_at DESC
            """
        )
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as exc:
        log.warning("Failed to read cost records from PostgreSQL: %s", exc)
        # Fallback to file log
        return iter_cost_records()


def latest_cost_for_source(source: str) -> Optional[Dict[str, Any]]:
    records = [r for r in iter_cost_records() if r.get("source") == source]
    if not records:
        return None
    records.sort(key=lambda r: r.get("created_at") or "")
    return records[-1]


__all__ = [
    "record_run_cost",
    "iter_cost_records",
    "iter_cost_records_from_db",
    "latest_cost_for_source",
    "CostRecord",
    "COST_DB_PATH",
    "COST_LOG_PATH",
]
