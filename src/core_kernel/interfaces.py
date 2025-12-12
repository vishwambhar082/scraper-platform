"""
Core Kernel Interfaces Module

Defines abstract base classes and interfaces for the core kernel.
Provides contracts for processors, steps, and pipeline components.

Author: Scraper Platform Team
"""

import logging
from typing import Dict, Any, List, Optional, Protocol
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class StepType(str, Enum):
    """Types of pipeline steps."""
    FETCH = "fetch"
    PARSE = "parse"
    TRANSFORM = "transform"
    VALIDATE = "validate"
    EXPORT = "export"
    CUSTOM = "custom"


class ExecutionStatus(str, Enum):
    """Execution status values."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepResult:
    """Result of step execution."""

    status: ExecutionStatus
    data: Any
    error: Optional[Exception] = None
    metadata: Optional[Dict[str, Any]] = None

    @property
    def is_success(self) -> bool:
        """Check if step succeeded."""
        return self.status == ExecutionStatus.COMPLETED

    @property
    def is_failure(self) -> bool:
        """Check if step failed."""
        return self.status == ExecutionStatus.FAILED


class IProcessor(ABC):
    """
    Interface for data processors.

    All processors must implement this interface to be compatible
    with the pipeline execution engine.
    """

    @abstractmethod
    def process(self, data: Any, context: Dict[str, Any]) -> Any:
        """
        Process input data.

        Args:
            data: Input data
            context: Execution context

        Returns:
            Processed data
        """
        pass

    @abstractmethod
    def validate_input(self, data: Any) -> bool:
        """
        Validate input data.

        Args:
            data: Data to validate

        Returns:
            True if valid
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        Get processor name.

        Returns:
            Processor name
        """
        pass


class IStep(ABC):
    """
    Interface for pipeline steps.

    Steps are the building blocks of pipelines and encapsulate
    processors with configuration and dependencies.
    """

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> StepResult:
        """
        Execute the step.

        Args:
            context: Execution context

        Returns:
            Step execution result
        """
        pass

    @abstractmethod
    def validate(self) -> bool:
        """
        Validate step configuration.

        Returns:
            True if valid
        """
        pass

    @abstractmethod
    def get_dependencies(self) -> List[str]:
        """
        Get list of step dependencies.

        Returns:
            List of step names this step depends on
        """
        pass

    @abstractmethod
    def get_type(self) -> StepType:
        """
        Get step type.

        Returns:
            Step type
        """
        pass


class IPipeline(ABC):
    """
    Interface for pipelines.

    Pipelines orchestrate the execution of multiple steps
    with dependency management and error handling.
    """

    @abstractmethod
    def add_step(self, step: IStep) -> None:
        """
        Add a step to the pipeline.

        Args:
            step: Step to add
        """
        pass

    @abstractmethod
    def compile(self) -> bool:
        """
        Compile the pipeline (resolve dependencies, validate).

        Returns:
            True if compilation succeeded
        """
        pass

    @abstractmethod
    def execute(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, StepResult]:
        """
        Execute the pipeline.

        Args:
            context: Optional execution context

        Returns:
            Dictionary mapping step names to results
        """
        pass

    @abstractmethod
    def get_execution_order(self) -> List[str]:
        """
        Get the execution order of steps.

        Returns:
            Ordered list of step names
        """
        pass


class IStorage(ABC):
    """
    Interface for storage backends.

    Provides abstraction for different storage systems
    (filesystem, database, cloud, etc.).
    """

    @abstractmethod
    def save(self, key: str, data: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Save data to storage.

        Args:
            key: Storage key
            data: Data to save
            metadata: Optional metadata

        Returns:
            True if saved successfully
        """
        pass

    @abstractmethod
    def load(self, key: str) -> Optional[Any]:
        """
        Load data from storage.

        Args:
            key: Storage key

        Returns:
            Loaded data or None if not found
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete data from storage.

        Args:
            key: Storage key

        Returns:
            True if deleted successfully
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if key exists in storage.

        Args:
            key: Storage key

        Returns:
            True if exists
        """
        pass


class ICache(ABC):
    """
    Interface for caching systems.

    Provides temporary storage for frequently accessed data.
    """

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds

        Returns:
            True if set successfully
        """
        pass

    @abstractmethod
    def invalidate(self, key: str) -> bool:
        """
        Invalidate cache entry.

        Args:
            key: Cache key

        Returns:
            True if invalidated
        """
        pass

    @abstractmethod
    def clear(self) -> bool:
        """
        Clear all cache entries.

        Returns:
            True if cleared successfully
        """
        pass


class IExecutor(ABC):
    """
    Interface for execution engines.

    Handles the actual execution of pipelines with
    scheduling, parallelization, and resource management.
    """

    @abstractmethod
    def submit(self, pipeline: IPipeline, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Submit a pipeline for execution.

        Args:
            pipeline: Pipeline to execute
            context: Optional execution context

        Returns:
            Execution ID
        """
        pass

    @abstractmethod
    def get_status(self, execution_id: str) -> ExecutionStatus:
        """
        Get execution status.

        Args:
            execution_id: Execution ID

        Returns:
            Current status
        """
        pass

    @abstractmethod
    def cancel(self, execution_id: str) -> bool:
        """
        Cancel an execution.

        Args:
            execution_id: Execution ID

        Returns:
            True if cancelled
        """
        pass

    @abstractmethod
    def get_result(self, execution_id: str) -> Optional[Dict[str, StepResult]]:
        """
        Get execution results.

        Args:
            execution_id: Execution ID

        Returns:
            Execution results or None
        """
        pass


class IValidator(ABC):
    """
    Interface for validators.

    Validates data, configurations, and pipeline definitions.
    """

    @abstractmethod
    def validate(self, data: Any) -> bool:
        """
        Validate data.

        Args:
            data: Data to validate

        Returns:
            True if valid
        """
        pass

    @abstractmethod
    def get_errors(self) -> List[str]:
        """
        Get validation errors.

        Returns:
            List of error messages
        """
        pass


class ITransformer(ABC):
    """
    Interface for data transformers.

    Transforms data from one format to another.
    """

    @abstractmethod
    def transform(self, data: Any, config: Optional[Dict[str, Any]] = None) -> Any:
        """
        Transform data.

        Args:
            data: Input data
            config: Optional transformation config

        Returns:
            Transformed data
        """
        pass

    @abstractmethod
    def supports_type(self, data_type: type) -> bool:
        """
        Check if transformer supports a data type.

        Args:
            data_type: Data type to check

        Returns:
            True if supported
        """
        pass


class IExporter(ABC):
    """
    Interface for data exporters.

    Exports data to various formats and destinations.
    """

    @abstractmethod
    def export(
        self,
        data: Any,
        destination: str,
        options: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Export data.

        Args:
            data: Data to export
            destination: Export destination
            options: Optional export options

        Returns:
            True if exported successfully
        """
        pass

    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported export formats.

        Returns:
            List of format names
        """
        pass


class IMonitor(ABC):
    """
    Interface for monitoring systems.

    Monitors pipeline execution and system health.
    """

    @abstractmethod
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Record a metric.

        Args:
            name: Metric name
            value: Metric value
            tags: Optional metric tags
        """
        pass

    @abstractmethod
    def increment_counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Increment a counter.

        Args:
            name: Counter name
            tags: Optional counter tags
        """
        pass

    @abstractmethod
    def record_timing(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Record a timing metric.

        Args:
            name: Timing name
            duration: Duration in seconds
            tags: Optional timing tags
        """
        pass


# Protocol for callable processors (duck typing support)
class ProcessorCallable(Protocol):
    """Protocol for callable processor objects."""

    def __call__(self, data: Any, context: Dict[str, Any]) -> Any:
        """Process data."""
        ...
