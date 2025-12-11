# file: src/run_tracking/airflow_linker.py
"""
Utility functions to map scraper run_ids to Airflow DAG runs / task instances.
"""

from __future__ import annotations

from typing import Optional


def build_airflow_run_url(
    base_url: str,
    dag_id: str,
    run_id: str,
) -> str:
    """
    Construct a link to the Airflow UI for a given run.
    """
    base = base_url.rstrip("/")
    return f"{base}/dags/{dag_id}/grid?dag_run_id={run_id}"


def resolve_dag_id_for_source(source_name: str) -> Optional[str]:
    """
    Map a logical source (e.g. 'alfabeta') to an Airflow DAG ID.

    Stub implementation returns source_name; override if you use a naming
    convention like 'scraper_{source}'.
    """
    return f"scraper_{source_name}"
