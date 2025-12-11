"""
Programmatic entry point for running scraper pipelines.

This module provides a single function that can be called from Airflow
or other orchestrators to execute scraper runs with full context.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from src.common.logging_utils import get_logger
from src.pipeline import PipelineRunner, PipelineCompiler, UnifiedRegistry
from src.run_tracking.recorder import RunRecorder
from src.run_tracking.models import RunRecord
from pathlib import Path

log = get_logger("run-pipeline-entrypoint")

# DSL root directory
DSL_ROOT = Path(__file__).resolve().parents[2] / "dsl"


def run_pipeline(
    source: str,
    run_type: str = "FULL_REFRESH",
    params: Optional[Dict[str, Any]] = None,
    environment: str = "prod",
    jira_issue_key: Optional[str] = None,
    airflow_dag_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a scraper pipeline programmatically.

    This is the main entry point called by Airflow or other orchestrators.

    Args:
        source: Scraper source name (e.g., 'alfabeta')
        run_type: Type of run ('FULL_REFRESH', 'DELTA', 'SINGLE_PRODUCT')
        params: Additional parameters (filters, date ranges, etc.)
        environment: Environment name ('dev', 'staging', 'prod')
        jira_issue_key: Optional Jira issue key for tracking
        airflow_dag_run_id: Optional Airflow DAG run ID for correlation

    Returns:
        Dict with:
            - status: 'success' or 'failed'
            - run_id: Platform run ID
            - source: Source name
            - item_count: Number of items processed (if available)
            - error: Error message if failed
    """
    run_id = f"RUN-{datetime.utcnow().strftime('%Y-%m-%d')}-{uuid.uuid4().hex[:6].upper()}"
    params = params or {}

    log.info(
        "Starting pipeline run",
        extra={
            "run_id": run_id,
            "source": source,
            "run_type": run_type,
            "environment": environment,
            "jira_issue_key": jira_issue_key,
            "airflow_dag_run_id": airflow_dag_run_id,
        },
    )

    try:
        # Initialize run recorder
        recorder = RunRecorder()
        recorder.start_run(
            run_id=run_id,
            source=source,
            metadata={
                "run_type": run_type,
                "environment": environment,
                "jira_issue_key": jira_issue_key,
                "airflow_dag_run_id": airflow_dag_run_id,
                "params": params,
            },
        )

        # Load DSL components and compile pipeline
        components_yaml = DSL_ROOT / "components.yaml"
        pipeline_yaml = DSL_ROOT / "pipelines" / f"{source}.yaml"

        if not components_yaml.exists():
            raise FileNotFoundError(f"DSL components file not found: {components_yaml}")

        if not pipeline_yaml.exists():
            raise FileNotFoundError(f"Pipeline file not found: {pipeline_yaml}")

        # Use unified pipeline system
        registry = UnifiedRegistry.from_yaml(components_yaml)
        compiler = PipelineCompiler(registry)
        compiled = compiler.compile_from_file(pipeline_yaml)

        # Execute pipeline with unified runner
        runner = PipelineRunner()
        result = runner.run(
            pipeline=compiled,
            source=source,
            environment=environment,
            run_type=run_type,
            params=params,
        )

        # Extract item count from result
        item_count = result.item_count

        # Record completion
        recorder.finish_run(
            run_id=run_id,
            source=source,
            status="success",
            metadata={"item_count": item_count, "results": str(results)[:500]},
        )

        log.info(
            "Pipeline run completed successfully",
            extra={"run_id": run_id, "source": source, "item_count": item_count},
        )

        return {
            "status": "success",
            "run_id": run_id,
            "source": source,
            "item_count": item_count,
            "error": None,
        }

    except Exception as exc:
        error_msg = str(exc)
        log.error(
            "Pipeline run failed",
            extra={
                "run_id": run_id,
                "source": source,
                "error": error_msg,
            },
            exc_info=True,
        )

        # Record failure
        try:
            recorder = RunRecorder()
            recorder.finish_run(
                run_id=run_id,
                source=source,
                status="failed",
                metadata={"error": error_msg},
            )
        except Exception:
            pass  # Best effort

        return {
            "status": "failed",
            "run_id": run_id,
            "source": source,
            "item_count": None,
            "error": error_msg,
        }


def run_pipeline_cli() -> None:
    """CLI entry point for running pipelines."""
    import argparse

    parser = argparse.ArgumentParser(description="Run a scraper pipeline")
    parser.add_argument("--source", required=True, help="Source name (e.g., alfabeta)")
    parser.add_argument("--run-type", default="FULL_REFRESH", help="Run type")
    parser.add_argument("--environment", default="prod", help="Environment")
    parser.add_argument("--jira-issue-key", help="Jira issue key")
    parser.add_argument("--airflow-dag-run-id", help="Airflow DAG run ID")
    parser.add_argument("--params", help="JSON parameters")

    args = parser.parse_args()

    params = {}
    if args.params:
        import json

        params = json.loads(args.params)

    result = run_pipeline(
        source=args.source,
        run_type=args.run_type,
        params=params,
        environment=args.environment,
        jira_issue_key=args.jira_issue_key,
        airflow_dag_run_id=args.airflow_dag_run_id,
    )

    print(f"Status: {result['status']}")
    print(f"Run ID: {result['run_id']}")
    if result["item_count"]:
        print(f"Items: {result['item_count']}")
    if result["error"]:
        print(f"Error: {result['error']}")

    exit(0 if result["status"] == "success" else 1)


if __name__ == "__main__":
    run_pipeline_cli()

