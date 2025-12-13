"""Airflow DAG for sample_source pipeline via modern unified pipeline system."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

from src.pipeline.compiler import PipelineCompiler
from src.pipeline.registry import UnifiedRegistry
from src.pipeline.runner import PipelineRunner

DSL_ROOT = Path(__file__).resolve().parents[0].parent / "dsl"


def _resolve_runtime_env(context) -> Optional[str]:
    """Extract environment from Airflow context or env var."""
    from src.common.config_loader import get_runtime_env

    return get_runtime_env(default=None)


def _run_sample_source_pipeline(**context):
    """
    Task callable that runs the sample_source pipeline via the unified pipeline system.

    The pipeline compiles dsl/pipelines/sample_source.yaml against dsl/components.yaml,
    ensuring production runs stay aligned with the declared component graph
    instead of directly calling the module entrypoint.
    """

    registry = UnifiedRegistry.from_yaml(DSL_ROOT / "components.yaml")
    compiler = PipelineCompiler(registry)
    compiled = compiler.compile_from_file(DSL_ROOT / "pipelines" / "sample_source.yaml")

    runner = PipelineRunner()
    env = _resolve_runtime_env(context) or "dev"
    result = runner.run(
        pipeline=compiled,
        source="sample_source",
        environment=env,
        run_type="FULL_REFRESH"
    )

    print(f"[Sample Source DAG] Pipeline run {result.status}. Duration: {result.duration_seconds:.2f}s")
    print(f"[Sample Source DAG] Items processed: {result.item_count}")

    # Push run_id to XCom
    return result.run_id


default_args = {
    "owner": "scraper",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="scraper_sample_source",
    description="Sample source pipeline (DSL-driven)",
    default_args=default_args,
    schedule_interval=None,  # Manual trigger only
    start_date=datetime.now() - timedelta(days=1),
    catchup=False,
    tags=["sample", "dsl"],
) as dag:

    run_sample_source = PythonOperator(
        task_id="run_sample_source_pipeline",
        python_callable=_run_sample_source_pipeline,
        provide_context=True,
    )
