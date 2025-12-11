from __future__ import annotations

from typing import List, Dict, Any
import logging
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)


class DBExporter:
    """Minimal Postgres exporter for batch inserts."""

    def __init__(self, dsn: str, target_table: str, batch_size: int = 500) -> None:
        self.dsn = dsn
        self.target_table = target_table
        self.batch_size = batch_size

    def export(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not records:
            logger.info("DBExporter: no records to export")
            return {"inserted": 0}

        conn = psycopg2.connect(self.dsn)
        conn.autocommit = False
        inserted = 0
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                for i in range(0, len(records), self.batch_size):
                    batch = records[i : i + self.batch_size]
                    logger.info(
                        "Exporting batch %s..%s of %s",
                        i,
                        i + len(batch),
                        len(records),
                    )
                    self._insert_batch(cur, batch)
                    inserted += len(batch)
                conn.commit()
        except Exception as exc:  # pragma: no cover - runtime guard
            conn.rollback()
            logger.exception("DB export failed: %s", exc)
            raise
        finally:
            conn.close()
        return {"inserted": inserted}

    def _insert_batch(self, cur, batch: List[Dict[str, Any]]) -> None:
        sql = f"""
        INSERT INTO {self.target_table} (
            product_name,
            manufacturer,
            strength,
            pack_size,
            price,
            raw
        ) VALUES %s
        """
        values = []
        for rec in batch:
            values.append(
                (
                    rec.get("product_name"),
                    rec.get("manufacturer"),
                    rec.get("strength"),
                    rec.get("pack_size"),
                    rec.get("price"),
                    rec,
                )
            )
        psycopg2.extras.execute_values(cur, sql, values)


__all__ = ["DBExporter"]
