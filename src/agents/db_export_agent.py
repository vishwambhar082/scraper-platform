"""Agent that exports normalized records to the database."""

from __future__ import annotations

from typing import Iterable, Mapping, Optional

from src.common.logging_utils import get_logger
from src.processors.exporters.database_loader import DatabaseLoader

from .base import AgentConfig, AgentContext, BaseAgent

log = get_logger("agents.db-export")


class DbExportAgent(BaseAgent):
    """Persist normalized records to a configured database table."""

    def __init__(self, *, table_name: Optional[str] = None, config: Optional[AgentConfig] = None) -> None:
        super().__init__(config=config)
        self.table_name = table_name

    def _resolve_records(self, context: AgentContext) -> Iterable[Mapping[str, object]]:
        records = context.get("normalized_records") or context.get("records")
        if records is None:
            raise ValueError("DbExportAgent requires 'normalized_records' or 'records' in context")
        return records  # type: ignore[return-value]

    def _resolve_table(self, context: AgentContext) -> str:
        table = self.table_name or context.get_nested("db.table") or context.metadata.get("table")
        if not table:
            raise ValueError("DbExportAgent requires a table name via init or context.metadata['table']")
        return str(table)

    def run(self, context: AgentContext) -> AgentContext:
        records = list(self._resolve_records(context))
        table = self._resolve_table(context)

        if not records:
            log.info("No records to persist for table %s", table)
            context.metadata.setdefault("db_export", {})["rows"] = 0
            return context

        loader = DatabaseLoader(table)
        inserted = loader.load(records)
        context.metadata.setdefault("db_export", {})["rows"] = inserted
        log.info("Persisted %d records to %s", inserted, table)
        return context


__all__ = ["DbExportAgent"]
