from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from src.pipeline_pack.agents.orchestrator import run_configured_pipeline

default_args = {
    "owner": "scraper-platform",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def run_source_pipeline(**context):
    params = context.get("params", {})
    source = params.get("source", "alfabeta")
    env = params.get("env", "dev")
    ctx = run_configured_pipeline(source=source, env=env)
    return {
        "run_id": ctx.run_id,
        "errors": ctx.errors,
        "warnings": ctx.warnings,
        "export_summary": ctx.export_summary,
    }


dag = DAG(
    dag_id="agent_orchestrator_pack",
    default_args=default_args,
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["scraper", "agents"],
)

run_pipeline_task = PythonOperator(
    task_id="run_source_pipeline",
    python_callable=run_source_pipeline,
    provide_context=True,
    dag=dag,
)
