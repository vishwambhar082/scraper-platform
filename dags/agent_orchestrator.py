"""Airflow DAG to run agentic health checks and selector repair."""

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator


def _run_agentic_checks(**context):
    """Evaluate recent output drift and trigger repairs if needed."""

    from src.agents.agent_orchestrator import (
        load_recent_output_counts,
        orchestrate_source_repair,
    )

    sources = os.getenv("AGENTIC_SOURCES", "alfabeta").split(",")
    for source in [s.strip() for s in sources if s.strip()]:
        counts = load_recent_output_counts(source, limit=2)
        if not counts:
            print(f"[agent_orchestrator DAG] No outputs found for {source}; skipping")
            continue

        current_rows = counts[0]
        baseline_rows = counts[1] if len(counts) > 1 else counts[0]
        outcome = orchestrate_source_repair(
            source=source,
            baseline_rows=baseline_rows,
            current_rows=current_rows,
            validation_rate=None,
            selectors_path=None,
        )
        print(
            f"[agent_orchestrator DAG] {source}: drift_action={outcome.assessment.drift_decision.action} "
            f"repair={outcome.triggered_repair} notes={outcome.notes}"
        )


def _run_repair_loops(**context):
    """Trigger DeepAgent repair loop based on stored anomalies."""

    from src.agents.repair_loop import run_repair_loop

    sources = os.getenv("AGENTIC_SOURCES", "alfabeta").split(",")
    tenant_id = os.getenv("AGENTIC_TENANT_ID")
    max_patches = int(os.getenv("AGENTIC_MAX_PATCHES", "5"))

    for source in [s.strip() for s in sources if s.strip()]:
        print(f"[agent_orchestrator DAG] Running repair loop for {source}")
        run_repair_loop(source=source, max_patches=max_patches, tenant_id=tenant_id)


default_args = {
    "owner": "agent_orchestrator",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
    "retry_delay": timedelta(minutes=10),
}

with DAG(
    dag_id="agent_orchestrator_hourly",
    description="Agentic self-healing checks for scraper outputs",
    default_args=default_args,
    schedule_interval="0 * * * *",  # hourly
    start_date=datetime.now() - timedelta(days=1),
    catchup=False,
    tags=["agentic", "self-heal"],
) as dag:

    run_agentic_checks = PythonOperator(
        task_id="run_agentic_checks",
        python_callable=_run_agentic_checks,
        provide_context=True,
    )

    run_agentic_repairs = PythonOperator(
        task_id="run_agentic_repairs",
        python_callable=_run_repair_loops,
        provide_context=True,
    )

    run_agentic_checks >> run_agentic_repairs
