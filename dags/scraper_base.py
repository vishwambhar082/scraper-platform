"""Common helpers for scraper DAGs. Provides standardized DAG factory using unified pipeline runner."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

from src.pipeline import PipelineRunner, PipelineCompiler, UnifiedRegistry
from src.integrations.jira_airflow_integration import get_integration_service
from pathlib import Path

# Pipeline definitions location
DSL_ROOT = Path(__file__).resolve().parents[1] / "dsl"


def _extract_dag_conf(context: Dict[str, Any]) -> Dict[str, Any]:
    dag_run = context.get("dag_run") if context else None
    conf = getattr(dag_run, "conf", None) or {}
    return conf if isinstance(conf, dict) else {}


def _build_task_callable(source: str):
    """Build task callable that uses unified pipeline runner."""
    def _task_callable(**context: Any) -> Dict[str, Any]:
        conf = _extract_dag_conf(context)
        dag_run = context.get("dag_run")
        dag_run_id = dag_run.dag_run_id if dag_run else None

        run_type = conf.get("run_type", "FULL_REFRESH")
        params = conf.get("params", {})
        environment = conf.get("environment", "prod")
        jira_issue_key = conf.get("jira_issue_key")
        
        # Add Jira and Airflow metadata to params
        params["jira_issue_key"] = jira_issue_key
        params["airflow_dag_run_id"] = dag_run_id

        # Load and compile pipeline
        components_yaml = DSL_ROOT / "components.yaml"
        pipeline_yaml = DSL_ROOT / "pipelines" / f"{source}.yaml"
        
        registry = UnifiedRegistry.from_yaml(components_yaml)
        compiler = PipelineCompiler(registry)
        compiled = compiler.compile_from_file(pipeline_yaml)
        
        # Execute with unified runner
        runner = PipelineRunner()
        result = runner.run(
            pipeline=compiled,
            source=conf.get("source", source),
            environment=environment,
            run_type=run_type,
            params=params,
        )

        # Update Jira if issue key provided
        if jira_issue_key:
            integration_service = get_integration_service()
            if integration_service:
                integration_service.update_jira_on_completion(
                    issue_key=jira_issue_key,
                    status=result.status,
                    run_id=result.run_id,
                    dag_run_id=dag_run_id,
                    item_count=result.item_count,
                    error=result.error,
                )

        if result.status == "failed":
            raise RuntimeError(result.error or "Pipeline run failed")

        return {
            "status": result.status,
            "run_id": result.run_id,
            "item_count": result.item_count,
            "duration": result.duration_seconds,
        }

    return _task_callable


def build_scraper_dag(
    *,
    source: str,
    dag_id: str,
    description: str,
    schedule: Optional[str],
    tags: Optional[list[str]] = None,
    start_days_ago: int = 1,
) -> DAG:
    default_args = {
        "owner": "scraper",
        "depends_on_past": False,
        "email_on_failure": False,
        "email_on_retry": False,
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    }

    dag = DAG(
        dag_id=dag_id,
        description=description,
        default_args=default_args,
        schedule_interval=schedule,
        start_date=datetime.now() - timedelta(days=start_days_ago),
        catchup=False,
        tags=tags or ["scraper", source],
    )

    with dag:
        PythonOperator(
            task_id=f"run_{source}_pipeline",
            python_callable=_build_task_callable(source),
            provide_context=True,
        )

    return dag

