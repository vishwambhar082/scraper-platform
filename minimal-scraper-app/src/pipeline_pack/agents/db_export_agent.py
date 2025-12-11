from __future__ import annotations

import logging
import os

from .base import BaseAgent, AgentContext
from src.pipeline_pack.exporters.db_exporter import DBExporter

logger = logging.getLogger(__name__)


class DbExportAgent(BaseAgent):
    name = "db_export"

    def execute(self, ctx: AgentContext) -> AgentContext:
        if not ctx.records:
            ctx.add_warning("DbExportAgent: no records to export")
            return ctx

        dsn = self.config.get("dsn") or os.getenv("SCRAPER_DB_DSN")
        table = self.config.get("table", f"{ctx.source}_raw")
        if not dsn:
            ctx.add_error("DbExportAgent: no DSN configured")
            return ctx

        exporter = DBExporter(dsn=dsn, target_table=table)
        summary = exporter.export(ctx.records)
        ctx.export_summary = summary
        return ctx


__all__ = ["DbExportAgent"]
