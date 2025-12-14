"""
Resource monitoring for execution engine.
"""

import psutil
import threading
import time
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ResourceSnapshot:
    """Snapshot of system resources"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    disk_percent: float
    process_count: int
    open_file_count: int


class ResourceMonitor:
    """
    Monitor system resources for execution engine.

    Tracks CPU, memory, disk usage and can enforce limits.
    """

    def __init__(
        self,
        sample_interval: float = 1.0,
        cpu_limit_percent: Optional[float] = None,
        memory_limit_mb: Optional[float] = None
    ):
        """
        Initialize resource monitor.

        Args:
            sample_interval: Seconds between samples
            cpu_limit_percent: CPU usage limit (percentage)
            memory_limit_mb: Memory usage limit (MB)
        """
        self.sample_interval = sample_interval
        self.cpu_limit_percent = cpu_limit_percent
        self.memory_limit_mb = memory_limit_mb

        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._current_snapshot: Optional[ResourceSnapshot] = None
        self._lock = threading.Lock()
        self._limit_callbacks: list = []

    def start(self):
        """Start resource monitoring"""
        if self._running:
            return

        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="ResourceMonitor"
        )
        self._monitor_thread.start()
        logger.info("ResourceMonitor started")

    def stop(self):
        """Stop resource monitoring"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("ResourceMonitor stopped")

    def get_current_snapshot(self) -> Optional[ResourceSnapshot]:
        """Get most recent resource snapshot"""
        with self._lock:
            return self._current_snapshot

    def subscribe_limit_exceeded(self, callback: Callable[[str, float], None]):
        """
        Subscribe to limit exceeded events.

        Args:
            callback: Function to call with (resource_type, value)
        """
        self._limit_callbacks.append(callback)

    def _monitor_loop(self):
        """Main monitoring loop"""
        logger.info("ResourceMonitor loop started")

        while self._running:
            try:
                # Collect resource metrics
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')

                # Process info
                try:
                    process = psutil.Process()
                    process_count = len(psutil.pids())
                    open_files = len(process.open_files())
                except:
                    process_count = 0
                    open_files = 0

                # Create snapshot
                snapshot = ResourceSnapshot(
                    timestamp=datetime.utcnow(),
                    cpu_percent=cpu_percent,
                    memory_percent=memory.percent,
                    memory_available_mb=memory.available / (1024 * 1024),
                    disk_percent=disk.percent,
                    process_count=process_count,
                    open_file_count=open_files
                )

                with self._lock:
                    self._current_snapshot = snapshot

                # Check limits
                self._check_limits(snapshot)

                # Sleep until next sample
                time.sleep(self.sample_interval)

            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                time.sleep(5)  # Back off on error

        logger.info("ResourceMonitor loop stopped")

    def _check_limits(self, snapshot: ResourceSnapshot):
        """Check if resource limits are exceeded"""
        # Check CPU limit
        if self.cpu_limit_percent and snapshot.cpu_percent > self.cpu_limit_percent:
            self._emit_limit_exceeded('cpu', snapshot.cpu_percent)
            logger.warning(f"CPU limit exceeded: {snapshot.cpu_percent:.1f}% > {self.cpu_limit_percent}%")

        # Check memory limit
        if self.memory_limit_mb:
            memory_used_mb = (100 - snapshot.memory_percent) / 100 * snapshot.memory_available_mb
            if memory_used_mb > self.memory_limit_mb:
                self._emit_limit_exceeded('memory', memory_used_mb)
                logger.warning(f"Memory limit exceeded: {memory_used_mb:.1f}MB > {self.memory_limit_mb}MB")

    def _emit_limit_exceeded(self, resource_type: str, value: float):
        """Emit limit exceeded event"""
        for callback in self._limit_callbacks:
            try:
                callback(resource_type, value)
            except Exception as e:
                logger.error(f"Limit callback error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get resource monitor statistics"""
        snapshot = self.get_current_snapshot()
        if not snapshot:
            return {}

        return {
            'cpu_percent': snapshot.cpu_percent,
            'memory_percent': snapshot.memory_percent,
            'memory_available_mb': snapshot.memory_available_mb,
            'disk_percent': snapshot.disk_percent,
            'process_count': snapshot.process_count,
            'open_file_count': snapshot.open_file_count,
            'timestamp': snapshot.timestamp.isoformat(),
            'is_running': self._running
        }
