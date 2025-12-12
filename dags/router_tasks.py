"""
Router DAG that pre-computes proxy/account assignments per source.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import yaml
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

from src.resource_manager.proxy_router import pick_healthy_proxy

REGISTRY_PATH = Path(__file__).resolve().parents[1] / "config" / "source_registry.yaml"


def _load_sources() -> List[str]:
    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8")) or {}
    return list((data.get("sources") or {}).keys())


def _route_sources(**_context) -> Dict[str, Dict[str, str]]:
    plan: Dict[str, Dict[str, str]] = {}
    for source in _load_sources():
        proxy = pick_healthy_proxy(source)
        plan[source] = {"proxy": proxy or "direct"}
    return plan


with DAG(
    dag_id="router_tasks",
    description="Computes routing plans for scraper sources",
    schedule_interval="*/15 * * * *",
    start_date=datetime.now() - timedelta(days=1),
    catchup=False,
    tags=["router", "scraper"],
) as dag:
    PythonOperator(
        task_id="compute_routing_plan",
        python_callable=_route_sources,
    )
