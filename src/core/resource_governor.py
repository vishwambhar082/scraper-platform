"""
System-wide resource governor for desktop app.

Enforces CPU/memory/disk limits to prevent system freeze.
"""

import logging
import psutil
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from threading import RLock

logger = logging.getLogger(__name__)


@dataclass
class ResourceLimits:
    """Resource limit configuration."""
    max_cpu_percent: float = 80.0
    max_memory_percent: float = 70.0
    max_disk_percent: float = 90.0
    max_browsers: int = 3
    max_browser_memory_mb: int = 4096


@dataclass
class ResourceSnapshot:
    """Current resource usage snapshot."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    browser_count: int
    browser_memory_mb: float


class BrowserTracker:
    """Track active browser instances."""

    def __init__(self, max_browsers: int = 3):
        """Initialize browser tracker."""
        self._lock = RLock()
        self._browsers: Dict[str, Dict[str, Any]] = {}
        self.max_browsers = max_browsers

    def register(self, browser_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Register new browser instance."""
        with self._lock:
            if len(self._browsers) >= self.max_browsers:
                raise ResourceLimitError(f"Browser limit reached: {self.max_browsers}")

            self._browsers[browser_id] = {
                'created_at': datetime.utcnow(),
                'memory_mb': 0.0,
                'metadata': metadata or {}
            }

        logger.info(f"Browser registered: {browser_id} ({len(self._browsers)}/{self.max_browsers})")

    def unregister(self, browser_id: str):
        """Unregister browser instance."""
        with self._lock:
            if browser_id in self._browsers:
                del self._browsers[browser_id]
                logger.info(f"Browser unregistered: {browser_id}")

    def update_memory(self, browser_id: str, memory_mb: float):
        """Update browser memory usage."""
        with self._lock:
            if browser_id in self._browsers:
                self._browsers[browser_id]['memory_mb'] = memory_mb

    def get_count(self) -> int:
        """Get active browser count."""
        with self._lock:
            return len(self._browsers)

    def get_total_memory(self) -> float:
        """Get total memory usage (MB)."""
        with self._lock:
            return sum(b['memory_mb'] for b in self._browsers.values())

    def can_add_browser(self) -> bool:
        """Check if new browser can be added."""
        with self._lock:
            return len(self._browsers) < self.max_browsers


class ResourceGovernor:
    """
    System-wide resource governor.

    Enforces limits to prevent desktop app from freezing system.
    """

    def __init__(self, limits: Optional[ResourceLimits] = None):
        """
        Initialize resource governor.

        Args:
            limits: Resource limits configuration
        """
        self.limits = limits or ResourceLimits()
        self.browser_tracker = BrowserTracker(self.limits.max_browsers)
        self._lock = RLock()
        self._warnings: List[str] = []

    def check_resources(self) -> ResourceSnapshot:
        """
        Check current resource usage.

        Returns:
            Current resource snapshot
        """
        cpu = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        browser_count = self.browser_tracker.get_count()
        browser_memory = self.browser_tracker.get_total_memory()

        snapshot = ResourceSnapshot(
            timestamp=datetime.utcnow(),
            cpu_percent=cpu,
            memory_percent=memory,
            disk_percent=disk,
            browser_count=browser_count,
            browser_memory_mb=browser_memory
        )

        # Check warnings
        self._warnings.clear()

        if cpu > self.limits.max_cpu_percent:
            self._warnings.append(f"CPU usage high: {cpu:.1f}% (limit: {self.limits.max_cpu_percent}%)")

        if memory > self.limits.max_memory_percent:
            self._warnings.append(f"Memory usage high: {memory:.1f}% (limit: {self.limits.max_memory_percent}%)")

        if disk > self.limits.max_disk_percent:
            self._warnings.append(f"Disk usage high: {disk:.1f}% (limit: {self.limits.max_disk_percent}%)")

        if browser_memory > self.limits.max_browser_memory_mb:
            self._warnings.append(
                f"Browser memory exceeded: {browser_memory:.1f} MB "
                f"(limit: {self.limits.max_browser_memory_mb} MB)"
            )

        return snapshot

    def is_resource_available(self) -> bool:
        """
        Check if resources are available for new work.

        Returns:
            True if resources OK, False if constrained
        """
        snapshot = self.check_resources()

        return (
            snapshot.cpu_percent <= self.limits.max_cpu_percent and
            snapshot.memory_percent <= self.limits.max_memory_percent and
            snapshot.disk_percent <= self.limits.max_disk_percent and
            snapshot.browser_memory_mb <= self.limits.max_browser_memory_mb
        )

    def can_start_browser(self) -> bool:
        """Check if new browser can be started."""
        return (
            self.is_resource_available() and
            self.browser_tracker.can_add_browser()
        )

    def register_browser(self, browser_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Register new browser instance."""
        if not self.can_start_browser():
            raise ResourceLimitError("Cannot start browser: resource limits exceeded")

        self.browser_tracker.register(browser_id, metadata)

    def unregister_browser(self, browser_id: str):
        """Unregister browser instance."""
        self.browser_tracker.unregister(browser_id)

    def get_warnings(self) -> List[str]:
        """Get current resource warnings."""
        with self._lock:
            return self._warnings.copy()

    def apply_backpressure(self) -> bool:
        """
        Check if backpressure should be applied.

        Returns:
            True if resources are constrained
        """
        return len(self._warnings) > 0

    def get_stats(self) -> Dict[str, Any]:
        """Get resource statistics."""
        snapshot = self.check_resources()

        return {
            'timestamp': snapshot.timestamp.isoformat(),
            'cpu_percent': snapshot.cpu_percent,
            'memory_percent': snapshot.memory_percent,
            'disk_percent': snapshot.disk_percent,
            'browser_count': snapshot.browser_count,
            'browser_memory_mb': snapshot.browser_memory_mb,
            'limits': {
                'max_cpu_percent': self.limits.max_cpu_percent,
                'max_memory_percent': self.limits.max_memory_percent,
                'max_disk_percent': self.limits.max_disk_percent,
                'max_browsers': self.limits.max_browsers,
                'max_browser_memory_mb': self.limits.max_browser_memory_mb
            },
            'warnings': self.get_warnings(),
            'resource_available': self.is_resource_available(),
            'can_start_browser': self.can_start_browser()
        }


class ResourceLimitError(Exception):
    """Exception raised when resource limit is exceeded."""
    pass
