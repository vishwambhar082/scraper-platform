"""
Database loader for persisting normalized records.
"""
from __future__ import annotations

from typing import Iterable, Mapping

from psycopg2.extras import execute_values

from src.common import db


class DatabaseLoader:
    def __init__(self, table_name: str) -> None:
        self.table_name = table_name

    def load(self, records: Iterable[Mapping[str, object]]) -> int:
        batch = list(records)
        if not batch:
            return 0

        columns = list(batch[0].keys())
        values = [[record.get(col) for col in columns] for record in batch]
        with db.transaction() as conn, conn.cursor() as cur:
            execute_values(
                cur,
                f"INSERT INTO {self.table_name} ({', '.join(columns)}) VALUES %s",
                values,
            )
        return len(batch)

