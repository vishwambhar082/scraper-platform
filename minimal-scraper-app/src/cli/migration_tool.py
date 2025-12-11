"""
CLI wrapper to run SQL migrations programmatically.
"""
from __future__ import annotations

from scripts import run_sql_migrations


def apply_migrations_cli() -> int:
    run_sql_migrations.apply_migrations()
    return 0


def apply_migrations() -> None:
    run_sql_migrations.apply_migrations()

