"""Airflow DAG to execute agent pipelines defined in config/agents/pipelines.yaml."""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

from src.agents.base import AgentContext
from src.agents.orchestrator import run_configured_pipeline


def _run_pipeline(**context):
    params = context.get("params", {})
    source = params.get("source") or os.getenv("SCRAPER_SOURCE", "alfabeta")
    env = params.get("env") or os.getenv("SCRAPER_ENV")

    run_id = context.get("run_id") or "manual_run"
    execution_date = str(context.get("execution_date"))

    initial_ctx = AgentContext(
        metadata={
            "run_id": run_id,
            "execution_date": execution_date,
        }
    )

    result = run_configured_pipeline(source, env=env, initial_context=initial_ctx)
    return {"context": dict(result), "metadata": result.metadata}


def _default_args():
    return {
        "owner": "agent_pipeline",
        "depends_on_past": False,
        "email_on_failure": False,
        "email_on_retry": False,
        "retries": int(os.getenv("AGENT_PIPELINE_RETRIES", "0")),
        "retry_delay": timedelta(minutes=10),
    }


def create_dag() -> DAG:
    return DAG(
        dag_id="agent_pipeline_runner",
        description="Executes configured agent pipelines for a given source",
        default_args=_default_args(),
        schedule_interval=None,
        start_date=datetime.now() - timedelta(days=1),
        catchup=False,
        tags=["agentic", "pipeline"],
        params={"source": "alfabeta", "env": "dev"},
    )


dag = create_dag()

run_pipeline = PythonOperator(
    task_id="run_pipeline",
    python_callable=_run_pipeline,
    dag=dag,
    provide_context=True,
)
