"""
Profiler Module

Provides performance profiling for scraper pipelines.
Tracks execution time, memory usage, and resource consumption.

Author: Scraper Platform Team
"""

import logging
import time
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import sys

logger = logging.getLogger(__name__)


class ProfileMetric(str, Enum):
    """Profiling metrics."""
    EXECUTION_TIME = "execution_time"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    NETWORK_IO = "network_io"
    DISK_IO = "disk_io"


@dataclass
class ProfileMeasurement:
    """Single profiling measurement."""

    metric: ProfileMetric
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric": self.metric.value,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ProfileReport:
    """Profile execution report."""

    name: str
    start_time: datetime
    end_time: datetime
    duration: float
    measurements: List[ProfileMeasurement] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_time(self) -> float:
        """Get total execution time in seconds."""
        return self.duration

    def get_metric_summary(self, metric: ProfileMetric) -> Dict[str, float]:
        """
        Get summary statistics for a metric.

        Args:
            metric: Metric type

        Returns:
            Summary statistics
        """
        values = [
            m.value for m in self.measurements
            if m.metric == metric
        ]

        if not values:
            return {}

        return {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "total": sum(values),
            "count": len(values)
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration": self.duration,
            "measurements": [m.to_dict() for m in self.measurements],
            "metadata": self.metadata
        }


class Timer:
    """High-precision timer for profiling."""

    def __init__(self, name: str):
        """
        Initialize timer.

        Args:
            name: Timer name
        """
        self.name = name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.elapsed: float = 0.0

    def start(self) -> None:
        """Start timer."""
        self.start_time = time.perf_counter()

    def stop(self) -> float:
        """
        Stop timer.

        Returns:
            Elapsed time in seconds
        """
        if self.start_time is None:
            raise RuntimeError("Timer not started")

        self.end_time = time.perf_counter()
        self.elapsed = self.end_time - self.start_time
        return self.elapsed

    def reset(self) -> None:
        """Reset timer."""
        self.start_time = None
        self.end_time = None
        self.elapsed = 0.0

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False


class MemoryTracker:
    """Track memory usage during execution."""

    def __init__(self):
        """Initialize memory tracker."""
        self.baseline: Optional[int] = None
        self.peak: int = 0
        self.measurements: List[Tuple[float, int]] = []

    def start(self) -> None:
        """Start tracking."""
        self.baseline = self._get_memory_usage()
        self.peak = self.baseline

    def measure(self) -> int:
        """
        Take a memory measurement.

        Returns:
            Current memory usage in bytes
        """
        current = self._get_memory_usage()
        timestamp = time.perf_counter()
        self.measurements.append((timestamp, current))

        if current > self.peak:
            self.peak = current

        return current

    def get_delta(self) -> int:
        """
        Get memory delta from baseline.

        Returns:
            Memory increase in bytes
        """
        if self.baseline is None:
            return 0

        current = self._get_memory_usage()
        return current - self.baseline

    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss
        except ImportError:
            # Fallback to basic measurement
            return sys.getsizeof({})

    def get_peak_delta(self) -> int:
        """
        Get peak memory increase.

        Returns:
            Peak memory increase in bytes
        """
        if self.baseline is None:
            return 0
        return self.peak - self.baseline


class Profiler:
    """
    Performance profiler for scraper pipelines.

    Features:
    - Execution time tracking
    - Memory profiling
    - Function-level profiling
    - Bottleneck detection
    """

    def __init__(self, name: str = "profiler"):
        """
        Initialize profiler.

        Args:
            name: Profiler name
        """
        self.name = name
        self.enabled = True
        self.timers: Dict[str, Timer] = {}
        self.memory_tracker = MemoryTracker()
        self.measurements: List[ProfileMeasurement] = []
        self.start_time: Optional[datetime] = None
        logger.info(f"Initialized Profiler: {name}")

    def start(self) -> None:
        """Start profiling session."""
        self.start_time = datetime.now()
        self.memory_tracker.start()
        logger.debug("Profiling session started")

    def stop(self) -> ProfileReport:
        """
        Stop profiling session.

        Returns:
            Profile report
        """
        if self.start_time is None:
            raise RuntimeError("Profiler not started")

        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        # Add final memory measurement
        memory_delta = self.memory_tracker.get_delta()
        self.measurements.append(ProfileMeasurement(
            metric=ProfileMetric.MEMORY_USAGE,
            value=memory_delta / (1024 * 1024),  # Convert to MB
            unit="MB"
        ))

        report = ProfileReport(
            name=self.name,
            start_time=self.start_time,
            end_time=end_time,
            duration=duration,
            measurements=self.measurements
        )

        logger.info(
            f"Profiling session complete: {duration:.3f}s, "
            f"{len(self.measurements)} measurements"
        )

        return report

    def time_block(self, name: str) -> Timer:
        """
        Create a timer for a code block.

        Args:
            name: Block name

        Returns:
            Timer context manager
        """
        if name not in self.timers:
            self.timers[name] = Timer(name)

        timer = self.timers[name]
        timer.reset()
        return timer

    def record_time(self, name: str, duration: float) -> None:
        """
        Record execution time measurement.

        Args:
            name: Measurement name
            duration: Duration in seconds
        """
        measurement = ProfileMeasurement(
            metric=ProfileMetric.EXECUTION_TIME,
            value=duration,
            unit="seconds"
        )
        self.measurements.append(measurement)
        logger.debug(f"Recorded time: {name} = {duration:.3f}s")

    def record_memory(self, name: str, bytes_used: int) -> None:
        """
        Record memory usage.

        Args:
            name: Measurement name
            bytes_used: Bytes used
        """
        measurement = ProfileMeasurement(
            metric=ProfileMetric.MEMORY_USAGE,
            value=bytes_used / (1024 * 1024),  # Convert to MB
            unit="MB"
        )
        self.measurements.append(measurement)

    def profile_function(self, func: Callable) -> Callable:
        """
        Decorator to profile a function.

        Args:
            func: Function to profile

        Returns:
            Wrapped function
        """
        def wrapper(*args, **kwargs):
            if not self.enabled:
                return func(*args, **kwargs)

            func_name = func.__name__
            logger.debug(f"Profiling function: {func_name}")

            with self.time_block(func_name) as timer:
                result = func(*args, **kwargs)

            self.record_time(func_name, timer.elapsed)
            return result

        return wrapper

    def get_bottlenecks(self, threshold: float = 1.0) -> List[Dict[str, Any]]:
        """
        Identify performance bottlenecks.

        Args:
            threshold: Minimum time in seconds to be considered a bottleneck

        Returns:
            List of bottlenecks
        """
        bottlenecks = []

        time_measurements = [
            m for m in self.measurements
            if m.metric == ProfileMetric.EXECUTION_TIME
        ]

        for measurement in time_measurements:
            if measurement.value >= threshold:
                bottlenecks.append({
                    "metric": measurement.metric.value,
                    "value": measurement.value,
                    "unit": measurement.unit,
                    "timestamp": measurement.timestamp.isoformat()
                })

        # Sort by value (descending)
        bottlenecks.sort(key=lambda x: x["value"], reverse=True)

        return bottlenecks

    def get_summary(self) -> Dict[str, Any]:
        """
        Get profiling summary.

        Returns:
            Summary statistics
        """
        total_time = sum(
            m.value for m in self.measurements
            if m.metric == ProfileMetric.EXECUTION_TIME
        )

        total_memory = sum(
            m.value for m in self.measurements
            if m.metric == ProfileMetric.MEMORY_USAGE
        )

        return {
            "total_measurements": len(self.measurements),
            "total_time": total_time,
            "total_memory_mb": total_memory,
            "timers": len(self.timers),
            "bottlenecks": len(self.get_bottlenecks())
        }


class ProfilerContext:
    """Context manager for profiling code blocks."""

    def __init__(self, profiler: Profiler, name: str):
        """
        Initialize profiler context.

        Args:
            profiler: Profiler instance
            name: Block name
        """
        self.profiler = profiler
        self.name = name
        self.timer: Optional[Timer] = None

    def __enter__(self):
        """Enter profiling context."""
        self.timer = self.profiler.time_block(self.name)
        self.timer.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit profiling context."""
        if self.timer:
            self.timer.stop()
            self.profiler.record_time(self.name, self.timer.elapsed)
        return False


# Global profiler instance
_profiler: Optional[Profiler] = None


def get_profiler() -> Profiler:
    """
    Get the global profiler instance.

    Returns:
        Profiler singleton
    """
    global _profiler
    if _profiler is None:
        _profiler = Profiler()

    return _profiler


def profile_block(name: str) -> ProfilerContext:
    """
    Context manager for profiling a code block.

    Args:
        name: Block name

    Returns:
        Profiler context
    """
    profiler = get_profiler()
    return ProfilerContext(profiler, name)


def profile(func: Callable) -> Callable:
    """
    Decorator to profile a function.

    Args:
        func: Function to profile

    Returns:
        Wrapped function
    """
    profiler = get_profiler()
    return profiler.profile_function(func)
