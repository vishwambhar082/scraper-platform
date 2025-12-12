"""Airflow DAG for sample_source pipeline via DSL/kernel stack."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

from src.core_kernel.execution_engine import ExecutionEngine
from src.core_kernel.pipeline_compiler import PipelineCompiler
from src.core_kernel.registry import ComponentRegistry

DSL_ROOT = Path(__file__).resolve().parents[0].parent / "dsl"


def _resolve_runtime_env(context) -> Optional[str]:
    """Extract environment from Airflow context or env var."""
    from src.common.config_loader import get_runtime_env

    return get_runtime_env(default=None)


def _run_sample_source_pipeline(**context):
    """
    Task callable that runs the sample_source pipeline via the DSL/kernel stack.

    The kernel compiles dsl/pipelines/sample_source.yaml against dsl/components.yaml,
    ensuring production runs stay aligned with the declared component graph
    instead of directly calling the module entrypoint.
    """

    registry = ComponentRegistry.from_yaml(DSL_ROOT / "components.yaml")
    compiler = PipelineCompiler(registry)
    compiled = compiler.compile_from_file(DSL_ROOT / "pipelines" / "sample_source.yaml")

    engine = ExecutionEngine(registry)
    env = _resolve_runtime_env(context)
    results = engine.execute(compiled, runtime_params={"env": env})

    out_path = results.get("run_sample_pipeline")
    print(f"[Sample Source DAG] Sample source run completed. Output: {out_path}")
    # Push path to XCom
    return str(out_path)


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
