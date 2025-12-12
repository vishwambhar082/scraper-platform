"""
Airflow DAG that triggers deterministic replay runs for debugging.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

from src.tests_replay import replay_runner


def _run_replay(**context):
    dag_run = context.get("dag_run")
    conf = getattr(dag_run, "conf", None) or {}
    source = conf.get("source", "alfabeta")
    run_id = conf.get("run_id", "latest")
    replay_runner.run_replay(source=source, run_id=run_id)


with DAG(
    dag_id="scraper_replay_runner",
    description="Replays historical scraper runs for debugging",
    schedule_interval=None,
    start_date=datetime.now() - timedelta(days=1),
    catchup=False,
    tags=["replay", "debug"],
) as dag:
    PythonOperator(
        task_id="run_replay",
        python_callable=_run_replay,
        provide_context=True,
    )
