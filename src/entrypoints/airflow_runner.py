"""
Airflow Runner Module

Airflow-compatible wrapper for pipeline execution in DAGs.
Provides integration with Airflow XCom, task dependencies, and error handling.

Author: Scraper Platform Team
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class AirflowRunner:
    """
    Airflow-compatible pipeline runner.

    Features:
    - XCom integration for task data passing
    - Airflow Variable and Connection support
    - Proper error propagation for Airflow retry logic
    - Task context awareness
    """

    def __init__(self, task_instance: Optional[Any] = None):
        """
        Initialize Airflow runner.

        Args:
            task_instance: Airflow TaskInstance object
        """
        self.task_instance = task_instance
        self.context: Dict[str, Any] = {}
        logger.info("Initialized AirflowRunner")

    def run_pipeline(
        self,
        config_path: str,
        source: str,
        execution_date: Optional[datetime] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run pipeline in Airflow context.

        Args:
            config_path: Path to pipeline configuration
            source: Source name
            execution_date: Airflow execution date
            **kwargs: Additional pipeline parameters from Airflow context

        Returns:
            Pipeline execution results
        """
        try:
            logger.info(f"Starting Airflow pipeline run for source: {source}")
            logger.info(f"Execution date: {execution_date}")

            # Extract Airflow context
            self.context = self._extract_context(kwargs)

            # Get configuration
            config = self._load_config(config_path, source)

            # Merge with XCom data if available
            if self.task_instance:
                xcom_data = self._get_xcom_data()
                config = self._merge_config(config, xcom_data)

            # Import and run pipeline
            from ..entrypoints.run_pipeline import run_pipeline

            result = run_pipeline(
                config=config,
                source=source,
                execution_date=execution_date,
                **kwargs
            )

            # Push results to XCom
            if self.task_instance:
                self._push_xcom_results(result)

            logger.info(f"Airflow pipeline run completed for source: {source}")
            return result

        except Exception as e:
            logger.error(f"Airflow pipeline run failed: {e}")
            # Re-raise for Airflow retry logic
            raise

    def _extract_context(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Extract Airflow context from kwargs."""
        context = {}

        # Airflow context keys
        airflow_keys = [
            'dag', 'task', 'task_instance', 'execution_date',
            'run_id', 'dag_run', 'conf', 'params'
        ]

        for key in airflow_keys:
            if key in kwargs:
                context[key] = kwargs[key]

        logger.debug(f"Extracted Airflow context: {list(context.keys())}")
        return context

    def _load_config(self, config_path: str, source: str) -> Dict[str, Any]:
        """
        Load pipeline configuration.

        Args:
            config_path: Path to config file
            source: Source name

        Returns:
            Configuration dictionary
        """
        path = Path(config_path)

        if not path.exists():
            # Try source-specific config
            path = Path(f"config/sources/{source}.yaml")

        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        # Load YAML config
        import yaml
        with open(path, 'r') as f:
            config = yaml.safe_load(f)

        logger.debug(f"Loaded config from {path}")
        return config

    def _get_xcom_data(self) -> Dict[str, Any]:
        """Get data from XCom (previous tasks)."""
        if not self.task_instance:
            return {}

        try:
            # Get data from upstream tasks
            xcom_data = {}

            # Example: Get data from task with key 'pipeline_config'
            config_data = self.task_instance.xcom_pull(key='pipeline_config')
            if config_data:
                xcom_data['config'] = config_data

            # Get data from previous task
            prev_data = self.task_instance.xcom_pull(task_ids=None)
            if prev_data:
                xcom_data['previous_task'] = prev_data

            logger.debug(f"Retrieved XCom data: {list(xcom_data.keys())}")
            return xcom_data

        except Exception as e:
            logger.warning(f"Failed to get XCom data: {e}")
            return {}

    def _merge_config(
        self,
        config: Dict[str, Any],
        xcom_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge configuration with XCom data."""
        if 'config' in xcom_data:
            # Deep merge configs
            config.update(xcom_data['config'])
            logger.debug("Merged XCom config data")

        return config

    def _push_xcom_results(self, result: Dict[str, Any]) -> None:
        """Push results to XCom for downstream tasks."""
        if not self.task_instance:
            return

        try:
            # Push full results
            self.task_instance.xcom_push(key='pipeline_results', value=result)

            # Push summary metrics
            if 'metrics' in result:
                self.task_instance.xcom_push(key='metrics', value=result['metrics'])

            # Push record count
            if 'record_count' in result:
                self.task_instance.xcom_push(key='record_count', value=result['record_count'])

            logger.info("Pushed results to XCom")

        except Exception as e:
            logger.warning(f"Failed to push XCom data: {e}")

    def get_airflow_variable(self, key: str, default: Any = None) -> Any:
        """
        Get Airflow Variable.

        Args:
            key: Variable key
            default: Default value if not found

        Returns:
            Variable value
        """
        try:
            from airflow.models import Variable
            return Variable.get(key, default_var=default)
        except Exception as e:
            logger.warning(f"Failed to get Airflow variable {key}: {e}")
            return default

    def get_airflow_connection(self, conn_id: str) -> Optional[Any]:
        """
        Get Airflow Connection.

        Args:
            conn_id: Connection ID

        Returns:
            Connection object or None
        """
        try:
            from airflow.hooks.base import BaseHook
            return BaseHook.get_connection(conn_id)
        except Exception as e:
            logger.warning(f"Failed to get Airflow connection {conn_id}: {e}")
            return None


def run_airflow_pipeline(
    config_path: str,
    source: str,
    **context
) -> Dict[str, Any]:
    """
    Airflow task callable function.

    This is the main function to be called from Airflow DAGs.

    Args:
        config_path: Path to pipeline configuration
        source: Source name
        **context: Airflow context (automatically passed)

    Returns:
        Pipeline execution results

    Example:
        ```python
        from airflow import DAG
        from airflow.operators.python import PythonOperator
        from src.entrypoints.airflow_runner import run_airflow_pipeline

        with DAG('my_dag', ...) as dag:
            task = PythonOperator(
                task_id='run_scraper',
                python_callable=run_airflow_pipeline,
                op_kwargs={
                    'config_path': 'config/sources/alfabeta.yaml',
                    'source': 'alfabeta'
                },
                provide_context=True
            )
        ```
    """
    task_instance = context.get('task_instance')
    execution_date = context.get('execution_date')

    runner = AirflowRunner(task_instance=task_instance)

    return runner.run_pipeline(
        config_path=config_path,
        source=source,
        execution_date=execution_date,
        **context
    )


def create_airflow_pipeline_operator(
    task_id: str,
    config_path: str,
    source: str,
    dag: Any,
    **operator_kwargs
) -> Any:
    """
    Factory function to create Airflow PythonOperator for pipeline execution.

    Args:
        task_id: Airflow task ID
        config_path: Path to pipeline configuration
        source: Source name
        dag: Airflow DAG object
        **operator_kwargs: Additional PythonOperator arguments

    Returns:
        PythonOperator instance

    Example:
        ```python
        from airflow import DAG
        from src.entrypoints.airflow_runner import create_airflow_pipeline_operator

        with DAG('my_dag', ...) as dag:
            scraper_task = create_airflow_pipeline_operator(
                task_id='scrape_alfabeta',
                config_path='config/sources/alfabeta.yaml',
                source='alfabeta',
                dag=dag,
                retries=3
            )
        ```
    """
    try:
        from airflow.operators.python import PythonOperator

        return PythonOperator(
            task_id=task_id,
            python_callable=run_airflow_pipeline,
            op_kwargs={
                'config_path': config_path,
                'source': source
            },
            provide_context=True,
            dag=dag,
            **operator_kwargs
        )

    except ImportError:
        logger.error("Airflow not installed. Cannot create PythonOperator")
        raise


class AirflowPipelineOperator:
    """
    Custom Airflow operator wrapper for pipeline execution.

    Provides additional features like automatic retries, SLA monitoring,
    and error classification.
    """

    def __init__(
        self,
        task_id: str,
        config_path: str,
        source: str,
        retries: int = 3,
        retry_delay_minutes: int = 5
    ):
        """
        Initialize Airflow pipeline operator.

        Args:
            task_id: Task identifier
            config_path: Path to pipeline configuration
            source: Source name
            retries: Number of retry attempts
            retry_delay_minutes: Delay between retries in minutes
        """
        self.task_id = task_id
        self.config_path = config_path
        self.source = source
        self.retries = retries
        self.retry_delay_minutes = retry_delay_minutes

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute pipeline in Airflow context.

        Args:
            context: Airflow context

        Returns:
            Execution results
        """
        return run_airflow_pipeline(
            config_path=self.config_path,
            source=self.source,
            **context
        )
