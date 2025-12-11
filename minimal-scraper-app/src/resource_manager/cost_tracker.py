from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple

from src.common.logging_utils import get_logger
from src.processors.exporters.database_loader import _get_dsn

log = get_logger("cost-tracker")

try:
    import psycopg2
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore[attr-defined]


@dataclass
class CostEntry:
    source: str
    run_id: str
    cost_usd: float = 0.0


class CostTracker:
    """
    Track per-run cost in memory and optionally persist to DB.

    DB schema (add via migration):

        CREATE TABLE IF NOT EXISTS scraper.run_costs (
            source      text NOT NULL,
            run_id      text NOT NULL,
            cost_usd    numeric(18,6) NOT NULL,
            updated_at  timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (source, run_id)
        );
    """

    def __init__(self) -> None:
        self._entries: Dict[Tuple[str, str], CostEntry] = {}

    def add_cost(self, source: str, run_id: str, delta_usd: float) -> None:
        key = (source, run_id)
        entry = self._entries.get(key)
        if entry is None:
            entry = CostEntry(source=source, run_id=run_id, cost_usd=0.0)
            self._entries[key] = entry
        entry.cost_usd += float(delta_usd)
        log.debug(
            "CostTracker.add_cost",
            extra={"source": source, "run_id": run_id, "delta_usd": delta_usd},
        )

    def get_cost(self, source: str, run_id: str) -> float:
        entry = self._entries.get((source, run_id))
        return entry.cost_usd if entry else 0.0

    def flush_to_db(self) -> None:
        if not self._entries:
            return

        if psycopg2 is None:  # type: ignore[truthy-function]
            log.warning(
                "CostTracker.flush_to_db skipped: psycopg2 not available",
                extra={"entry_count": len(self._entries)},
            )
            return

        try:
            dsn = _get_dsn()
            with psycopg2.connect(dsn) as conn:  # type: ignore[call-arg]
                with conn.cursor() as cur:
                    for entry in self._entries.values():
                        cur.execute(
                            """
                            INSERT INTO scraper.run_costs (source, run_id, cost_usd)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (source, run_id)
                            DO UPDATE SET cost_usd = EXCLUDED.cost_usd,
                                          updated_at = now()
                            """,
                            (entry.source, entry.run_id, entry.cost_usd),
                        )
            log.info(
                "CostTracker.flush_to_db completed",
                extra={"entry_count": len(self._entries)},
            )
        except Exception as exc:  # pragma: no cover
            log.error(
                "CostTracker.flush_to_db failed",
                extra={"error": str(exc), "entry_count": len(self._entries)},
            )
