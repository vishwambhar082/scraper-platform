"""
Unified BaseScraper Interface

Provides a standardized interface for all scrapers with lifecycle hooks,
resource limits, and self-diagnostics.

Author: Scraper Platform Team
Date: 2025-12-13
"""

from __future__ import annotations

import time
import psutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.common.logging_utils import get_logger

log = get_logger("base_scraper")


@dataclass
class ScraperConfig:
    """Configuration for scraper execution."""

    source: str
    environment: str = "prod"
    run_type: str = "FULL_REFRESH"

    # Resource limits
    max_memory_mb: Optional[int] = None  # Max memory usage in MB
    max_cpu_percent: Optional[float] = None  # Max CPU usage percentage
    max_runtime_seconds: Optional[int] = None  # Max runtime in seconds

    # Execution settings
    max_retries: int = 3
    retry_backoff: float = 1.0
    timeout: float = 30.0

    # Feature flags
    enable_screenshots: bool = True
    enable_har_recording: bool = False
    enable_diagnostics: bool = True


@dataclass
class ScraperResult:
    """Result of scraper execution."""

    source: str
    status: str  # 'success', 'failed', 'partial'
    records: List[Dict[str, Any]]
    duration_seconds: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    diagnostics: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.status == "success"

    @property
    def record_count(self) -> int:
        return len(self.records)


@dataclass
class ScraperDiagnostics:
    """Diagnostic information from scraper execution."""

    peak_memory_mb: float
    peak_cpu_percent: float
    total_requests: int
    failed_requests: int
    average_response_time: float
    errors: List[str]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "peak_memory_mb": self.peak_memory_mb,
            "peak_cpu_percent": self.peak_cpu_percent,
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "average_response_time": self.average_response_time,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class ResourceMonitor:
    """Monitor resource usage during scraper execution."""

    def __init__(self):
        self.process = psutil.Process()
        self.peak_memory_mb = 0.0
        self.peak_cpu_percent = 0.0
        self.samples = []

    def sample(self) -> None:
        """Take a resource usage sample."""
        try:
            memory_mb = self.process.memory_info().rss / 1024 / 1024
            cpu_percent = self.process.cpu_percent(interval=0.1)

            self.peak_memory_mb = max(self.peak_memory_mb, memory_mb)
            self.peak_cpu_percent = max(self.peak_cpu_percent, cpu_percent)

            self.samples.append({
                "timestamp": time.time(),
                "memory_mb": memory_mb,
                "cpu_percent": cpu_percent,
            })

        except Exception as e:
            log.warning(f"Failed to sample resources: {e}")

    def check_limits(
        self, max_memory_mb: Optional[int], max_cpu_percent: Optional[float]
    ) -> Optional[str]:
        """Check if resource limits are exceeded.

        Args:
            max_memory_mb: Maximum memory in MB
            max_cpu_percent: Maximum CPU percentage

        Returns:
            Error message if limit exceeded, None otherwise
        """
        if max_memory_mb and self.peak_memory_mb > max_memory_mb:
            return f"Memory limit exceeded: {self.peak_memory_mb:.1f}MB > {max_memory_mb}MB"

        if max_cpu_percent and self.peak_cpu_percent > max_cpu_percent:
            return f"CPU limit exceeded: {self.peak_cpu_percent:.1f}% > {max_cpu_percent}%"

        return None


class BaseScraper(ABC):
    """
    Abstract base class for all scrapers.

    Lifecycle:
    1. __init__() - Initialize scraper with config
    2. setup() - Setup resources (engines, databases, etc.)
    3. run() - Execute scraping logic
    4. cleanup() - Clean up resources
    5. get_diagnostics() - Return diagnostic information

    Features:
    - Resource monitoring and limits
    - Lifecycle hooks
    - Self-diagnostics
    - Graceful error handling
    - Isolation support
    """

    def __init__(self, config: ScraperConfig):
        """Initialize scraper.

        Args:
            config: Scraper configuration
        """
        self.config = config
        self.source = config.source

        # Resource monitoring
        self._monitor = ResourceMonitor()
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None

        # Diagnostics
        self._total_requests = 0
        self._failed_requests = 0
        self._response_times: List[float] = []
        self._errors: List[str] = []
        self._warnings: List[str] = []

        # State
        self._initialized = False
        self._cleaned_up = False

    @abstractmethod
    def setup(self) -> None:
        """Setup scraper resources.

        This is called before run() and should initialize:
        - Engines (HTTP, browser, etc.)
        - Database connections
        - API clients
        - Temporary directories

        Raises:
            Exception on setup failure
        """
        pass

    @abstractmethod
    def scrape(self) -> List[Dict[str, Any]]:
        """Execute scraping logic.

        Returns:
            List of scraped records

        Raises:
            Exception on scraping failure
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up scraper resources.

        This is called after run() completes (success or failure) and should:
        - Close engines
        - Close database connections
        - Remove temporary files
        - Release any held resources

        Should not raise exceptions.
        """
        pass

    def run(self) -> ScraperResult:
        """Execute complete scraper lifecycle with resource monitoring.

        Returns:
            ScraperResult with records and diagnostics
        """
        self._start_time = time.time()
        log.info(f"Starting scraper: {self.source}")

        records = []
        status = "failed"
        error = None

        try:
            # Setup phase
            log.debug(f"Setting up scraper: {self.source}")
            self.setup()
            self._initialized = True

            # Check initial resource usage
            self._monitor.sample()

            # Scrape phase
            log.debug(f"Executing scrape: {self.source}")
            records = self.scrape()

            # Monitor resources periodically during execution
            self._monitor.sample()

            # Check resource limits
            limit_error = self._monitor.check_limits(
                self.config.max_memory_mb, self.config.max_cpu_percent
            )
            if limit_error:
                self._errors.append(limit_error)
                error = limit_error
                status = "failed"
            else:
                status = "success"

            log.info(
                f"Scraper completed: {self.source}",
                extra={
                    "record_count": len(records),
                    "status": status,
                },
            )

        except Exception as e:
            error = str(e)
            self._errors.append(error)
            log.error(f"Scraper failed: {self.source}", exc_info=True)
            status = "failed"

        finally:
            # Cleanup phase (always executes)
            try:
                log.debug(f"Cleaning up scraper: {self.source}")
                self.cleanup()
                self._cleaned_up = True
            except Exception as e:
                log.error(f"Cleanup failed for {self.source}: {e}", exc_info=True)

            self._end_time = time.time()

        # Final resource sample
        self._monitor.sample()

        # Check runtime limit
        duration = self._end_time - self._start_time
        if self.config.max_runtime_seconds and duration > self.config.max_runtime_seconds:
            warning = f"Runtime limit exceeded: {duration:.1f}s > {self.config.max_runtime_seconds}s"
            self._warnings.append(warning)

        # Build result
        result = ScraperResult(
            source=self.source,
            status=status,
            records=records,
            duration_seconds=duration,
            error=error,
            metadata={
                "environment": self.config.environment,
                "run_type": self.config.run_type,
            },
            diagnostics=self.get_diagnostics().to_dict() if self.config.enable_diagnostics else {},
        )

        return result

    def get_diagnostics(self) -> ScraperDiagnostics:
        """Get diagnostic information.

        Returns:
            ScraperDiagnostics with resource usage and error info
        """
        avg_response_time = (
            sum(self._response_times) / len(self._response_times)
            if self._response_times
            else 0.0
        )

        return ScraperDiagnostics(
            peak_memory_mb=self._monitor.peak_memory_mb,
            peak_cpu_percent=self._monitor.peak_cpu_percent,
            total_requests=self._total_requests,
            failed_requests=self._failed_requests,
            average_response_time=avg_response_time,
            errors=self._errors.copy(),
            warnings=self._warnings.copy(),
        )

    def health_check(self) -> Dict[str, Any]:
        """Perform self-diagnostic health check.

        Returns:
            Health check results
        """
        checks = {
            "initialized": self._initialized,
            "cleaned_up": self._cleaned_up,
            "has_errors": len(self._errors) > 0,
            "has_warnings": len(self._warnings) > 0,
            "resource_usage_normal": self._monitor.peak_memory_mb < 1000,  # Less than 1GB
        }

        overall_health = all([
            checks["initialized"],
            not checks["has_errors"],
            checks["resource_usage_normal"],
        ])

        return {
            "healthy": overall_health,
            "checks": checks,
            "diagnostics": self.get_diagnostics().to_dict(),
        }

    def _record_request(self, success: bool, response_time: float) -> None:
        """Record request metrics for diagnostics.

        Args:
            success: Whether request succeeded
            response_time: Response time in seconds
        """
        self._total_requests += 1
        if not success:
            self._failed_requests += 1
        self._response_times.append(response_time)

        # Sample resources periodically
        if self._total_requests % 10 == 0:
            self._monitor.sample()

    def _add_error(self, error: str) -> None:
        """Add error to diagnostics.

        Args:
            error: Error message
        """
        self._errors.append(error)
        log.error(f"Scraper error [{self.source}]: {error}")

    def _add_warning(self, warning: str) -> None:
        """Add warning to diagnostics.

        Args:
            warning: Warning message
        """
        self._warnings.append(warning)
        log.warning(f"Scraper warning [{self.source}]: {warning}")

    def __enter__(self):
        """Context manager entry."""
        self.setup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()

    def __del__(self):
        """Destructor - ensure cleanup is called."""
        if self._initialized and not self._cleaned_up:
            try:
                self.cleanup()
            except Exception:
                pass  # Suppress errors in destructor


# Example scraper implementation
class ExampleScraper(BaseScraper):
    """Example scraper implementation showing how to use BaseScraper."""

    def setup(self) -> None:
        """Setup example scraper."""
        # Initialize engines, databases, etc.
        log.info(f"Setting up {self.source} scraper")
        # Example: self.engine = HTTPEngine(config)

    def scrape(self) -> List[Dict[str, Any]]:
        """Execute scraping logic."""
        records = []

        # Example scraping logic
        for i in range(10):
            start_time = time.time()
            try:
                # Simulate scraping
                record = {"id": i, "data": f"example_{i}"}
                records.append(record)

                # Record successful request
                self._record_request(success=True, response_time=time.time() - start_time)

            except Exception as e:
                self._add_error(f"Failed to scrape record {i}: {e}")
                self._record_request(success=False, response_time=time.time() - start_time)

        return records

    def cleanup(self) -> None:
        """Cleanup example scraper."""
        log.info(f"Cleaning up {self.source} scraper")
        # Close engines, connections, etc.
        # Example: self.engine.cleanup()
