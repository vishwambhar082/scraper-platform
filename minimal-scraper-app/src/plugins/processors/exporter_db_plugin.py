# file: src/plugins/processors/exporter_db_plugin.py
"""
Plugin surface for DB export; thin wrapper over processors.exporters.
"""

from __future__ import annotations

from typing import Iterable, Mapping

from src.processors.exporters import database_loader


def export_records_to_db(records: Iterable[Mapping[str, object]]) -> None:
    """
    Persist an iterable of records into the target DB.

    The actual DB connection details should live in database_loader.
    """
    database_loader.export_records(records)
