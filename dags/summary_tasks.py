"""
Summary DAG publishing health metrics to disk.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

from src.observability import metrics


def _persist_metrics() -> str:
    path = metrics.persist_snapshot()
    return str(path)


def _cleanup_metrics() -> int:
    return metrics.cleanup_expired_metrics(ttl_seconds=3600)


with DAG(
    dag_id="summary_tasks",
    description="Publishes platform health summaries",
    schedule_interval="0 * * * *",
    start_date=datetime.now() - timedelta(days=1),
    catchup=False,
    tags=["observability", "summary"],
) as dag:
    persist = PythonOperator(
        task_id="persist_metrics_snapshot",
        python_callable=_persist_metrics,
    )

    cleanup = PythonOperator(
        task_id="cleanup_expired_metrics",
        python_callable=_cleanup_metrics,
    )

    persist >> cleanup
