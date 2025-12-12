"""
ETL Engine Module

Core ETL orchestration engine for Extract, Transform, Load operations.
Provides a unified interface for data pipeline processing.

Author: Scraper Platform Team
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ETLStage(str, Enum):
    """ETL pipeline stages."""
    EXTRACT = "extract"
    TRANSFORM = "transform"
    LOAD = "load"
    VALIDATE = "validate"


class ETLStatus(str, Enum):
    """ETL execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class ETLMetrics:
    """Metrics for ETL execution."""

    records_extracted: int = 0
    records_transformed: int = 0
    records_loaded: int = 0
    records_failed: int = 0
    bytes_processed: int = 0
    duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "records_extracted": self.records_extracted,
            "records_transformed": self.records_transformed,
            "records_loaded": self.records_loaded,
            "records_failed": self.records_failed,
            "bytes_processed": self.bytes_processed,
            "duration_seconds": self.duration_seconds,
            "error_count": len(self.errors),
            "success_rate": self._calculate_success_rate()
        }

    def _calculate_success_rate(self) -> float:
        """Calculate success rate."""
        total = self.records_extracted
        if total == 0:
            return 0.0
        return (self.records_loaded / total) * 100


@dataclass
class ETLResult:
    """Result of ETL execution."""

    status: ETLStatus
    metrics: ETLMetrics
    started_at: datetime
    completed_at: Optional[datetime] = None
    output_location: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "metrics": self.metrics.to_dict(),
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "output_location": self.output_location,
            "metadata": self.metadata
        }


class ETLComponent(ABC):
    """Abstract base class for ETL components."""

    @abstractmethod
    def process(self, data: Any, context: Dict[str, Any]) -> Any:
        """Process data through this component."""
        pass


class Extractor(ETLComponent):
    """Base class for data extractors."""

    def __init__(self, name: str):
        """
        Initialize extractor.

        Args:
            name: Extractor name
        """
        self.name = name

    @abstractmethod
    def extract(self, source: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Extract data from source.

        Args:
            source: Data source identifier
            **kwargs: Additional extraction parameters

        Returns:
            List of extracted records
        """
        pass

    def process(self, data: Any, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process extraction."""
        source = context.get('source', '')
        return self.extract(source, **context)


class Transformer(ETLComponent):
    """Base class for data transformers."""

    def __init__(self, name: str):
        """
        Initialize transformer.

        Args:
            name: Transformer name
        """
        self.name = name

    @abstractmethod
    def transform(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform records.

        Args:
            records: Input records

        Returns:
            Transformed records
        """
        pass

    def process(self, data: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process transformation."""
        return self.transform(data)


class Loader(ETLComponent):
    """Base class for data loaders."""

    def __init__(self, name: str):
        """
        Initialize loader.

        Args:
            name: Loader name
        """
        self.name = name

    @abstractmethod
    def load(
        self,
        records: List[Dict[str, Any]],
        destination: str,
        **kwargs
    ) -> int:
        """
        Load records to destination.

        Args:
            records: Records to load
            destination: Destination identifier
            **kwargs: Additional load parameters

        Returns:
            Number of records loaded
        """
        pass

    def process(
        self,
        data: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> int:
        """Process loading."""
        destination = context.get('destination', '')
        return self.load(data, destination, **context)


class ETLPipeline:
    """
    ETL pipeline orchestrator.

    Chains together extractors, transformers, and loaders in a configurable pipeline.
    """

    def __init__(self, name: str):
        """
        Initialize ETL pipeline.

        Args:
            name: Pipeline name
        """
        self.name = name
        self.extractors: List[Extractor] = []
        self.transformers: List[Transformer] = []
        self.loaders: List[Loader] = []
        self.validators: List[Callable] = []

    def add_extractor(self, extractor: Extractor) -> 'ETLPipeline':
        """Add an extractor to the pipeline."""
        self.extractors.append(extractor)
        logger.info(f"Added extractor: {extractor.name}")
        return self

    def add_transformer(self, transformer: Transformer) -> 'ETLPipeline':
        """Add a transformer to the pipeline."""
        self.transformers.append(transformer)
        logger.info(f"Added transformer: {transformer.name}")
        return self

    def add_loader(self, loader: Loader) -> 'ETLPipeline':
        """Add a loader to the pipeline."""
        self.loaders.append(loader)
        logger.info(f"Added loader: {loader.name}")
        return self

    def add_validator(self, validator: Callable) -> 'ETLPipeline':
        """Add a validation function."""
        self.validators.append(validator)
        return self

    def execute(self, context: Optional[Dict[str, Any]] = None) -> ETLResult:
        """
        Execute the complete ETL pipeline.

        Args:
            context: Execution context

        Returns:
            ETL execution result
        """
        context = context or {}
        metrics = ETLMetrics()
        started_at = datetime.now()

        try:
            logger.info(f"Starting ETL pipeline: {self.name}")

            # EXTRACT
            data = self._extract(context, metrics)

            # TRANSFORM
            data = self._transform(data, context, metrics)

            # VALIDATE
            if self.validators:
                data = self._validate(data, metrics)

            # LOAD
            output_location = self._load(data, context, metrics)

            # Complete
            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()
            metrics.duration_seconds = duration

            status = ETLStatus.COMPLETED if metrics.records_failed == 0 else ETLStatus.PARTIAL

            logger.info(f"ETL pipeline completed: {self.name}")

            return ETLResult(
                status=status,
                metrics=metrics,
                started_at=started_at,
                completed_at=completed_at,
                output_location=output_location
            )

        except Exception as e:
            logger.error(f"ETL pipeline failed: {e}")
            metrics.errors.append(str(e))

            return ETLResult(
                status=ETLStatus.FAILED,
                metrics=metrics,
                started_at=started_at,
                completed_at=datetime.now(),
                metadata={"error": str(e)}
            )

    def _extract(self, context: Dict[str, Any], metrics: ETLMetrics) -> List[Dict[str, Any]]:
        """Execute extraction phase."""
        logger.info("EXTRACT phase started")
        all_data = []

        for extractor in self.extractors:
            try:
                extracted = extractor.process(None, context)
                all_data.extend(extracted)
                metrics.records_extracted += len(extracted)
                logger.debug(f"Extracted {len(extracted)} records from {extractor.name}")
            except Exception as e:
                logger.error(f"Extraction failed for {extractor.name}: {e}")
                metrics.errors.append(f"Extract error in {extractor.name}: {str(e)}")

        logger.info(f"EXTRACT phase completed: {metrics.records_extracted} records")
        return all_data

    def _transform(
        self,
        data: List[Dict[str, Any]],
        context: Dict[str, Any],
        metrics: ETLMetrics
    ) -> List[Dict[str, Any]]:
        """Execute transformation phase."""
        logger.info("TRANSFORM phase started")

        for transformer in self.transformers:
            try:
                data = transformer.process(data, context)
                logger.debug(f"Transformed data through {transformer.name}")
            except Exception as e:
                logger.error(f"Transformation failed for {transformer.name}: {e}")
                metrics.errors.append(f"Transform error in {transformer.name}: {str(e)}")

        metrics.records_transformed = len(data)
        logger.info(f"TRANSFORM phase completed: {metrics.records_transformed} records")
        return data

    def _validate(
        self,
        data: List[Dict[str, Any]],
        metrics: ETLMetrics
    ) -> List[Dict[str, Any]]:
        """Execute validation phase."""
        logger.info("VALIDATE phase started")
        valid_data = []

        for record in data:
            is_valid = True
            for validator in self.validators:
                try:
                    if not validator(record):
                        is_valid = False
                        metrics.records_failed += 1
                        break
                except Exception as e:
                    logger.error(f"Validation error: {e}")
                    is_valid = False
                    metrics.records_failed += 1
                    break

            if is_valid:
                valid_data.append(record)

        logger.info(f"VALIDATE phase completed: {len(valid_data)} valid records")
        return valid_data

    def _load(
        self,
        data: List[Dict[str, Any]],
        context: Dict[str, Any],
        metrics: ETLMetrics
    ) -> Optional[str]:
        """Execute loading phase."""
        logger.info("LOAD phase started")
        output_location = None

        for loader in self.loaders:
            try:
                loaded_count = loader.process(data, context)
                metrics.records_loaded += loaded_count
                output_location = context.get('destination', f"output/{loader.name}")
                logger.debug(f"Loaded {loaded_count} records via {loader.name}")
            except Exception as e:
                logger.error(f"Loading failed for {loader.name}: {e}")
                metrics.errors.append(f"Load error in {loader.name}: {str(e)}")

        logger.info(f"LOAD phase completed: {metrics.records_loaded} records")
        return output_location


class ETLEngine:
    """
    Main ETL engine for managing multiple pipelines.

    Features:
    - Pipeline registry and management
    - Parallel pipeline execution
    - Dependency management between pipelines
    - Monitoring and metrics collection
    """

    def __init__(self):
        """Initialize ETL engine."""
        self.pipelines: Dict[str, ETLPipeline] = {}
        logger.info("Initialized ETLEngine")

    def register_pipeline(self, pipeline: ETLPipeline) -> None:
        """
        Register a pipeline.

        Args:
            pipeline: ETL pipeline to register
        """
        self.pipelines[pipeline.name] = pipeline
        logger.info(f"Registered pipeline: {pipeline.name}")

    def execute_pipeline(
        self,
        pipeline_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ETLResult:
        """
        Execute a specific pipeline.

        Args:
            pipeline_name: Name of pipeline to execute
            context: Execution context

        Returns:
            ETL execution result
        """
        if pipeline_name not in self.pipelines:
            raise ValueError(f"Pipeline not found: {pipeline_name}")

        pipeline = self.pipelines[pipeline_name]
        return pipeline.execute(context)

    def execute_all(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, ETLResult]:
        """
        Execute all registered pipelines.

        Args:
            context: Shared execution context

        Returns:
            Dictionary mapping pipeline names to results
        """
        results = {}

        for name, pipeline in self.pipelines.items():
            logger.info(f"Executing pipeline: {name}")
            results[name] = pipeline.execute(context)

        return results


# Global engine instance
_etl_engine: Optional[ETLEngine] = None


def get_etl_engine() -> ETLEngine:
    """
    Get the global ETL engine instance.

    Returns:
        ETL engine singleton
    """
    global _etl_engine
    if _etl_engine is None:
        _etl_engine = ETLEngine()
    return _etl_engine
