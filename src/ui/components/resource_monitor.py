"""
Resource Monitor Component.

Provides real-time system resource usage monitoring:
- CPU usage chart
- Memory usage chart
- Disk usage chart
- Network statistics
- Real-time updates using psutil
"""

from __future__ import annotations

from typing import List, Optional
from collections import deque

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QFrame,
)

from src.common.logging_utils import get_logger

log = get_logger("ui.components.resource_monitor")

# Import psutil if available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    log.warning("psutil not available - resource monitoring will show dummy data")


class MetricChart(QWidget):
    """A simple line chart for displaying a single metric over time."""

    def __init__(self, title: str, color: str = "#3b82f6", max_value: float = 100.0, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.title = title
        self.color = QColor(color)
        self.max_value = max_value
        self.data_points: deque = deque(maxlen=60)  # Keep last 60 data points
        self.setMinimumHeight(150)
        self.setMinimumWidth(200)

    def add_data_point(self, value: float) -> None:
        """Add a new data point to the chart."""
        self.data_points.append(value)
        self.update()

    def paintEvent(self, event) -> None:
        """Paint the chart."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor("#ffffff"))

        # Draw border
        painter.setPen(QPen(QColor("#e5e7eb"), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        if not self.data_points:
            # No data - show placeholder
            painter.setPen(QPen(QColor("#9ca3af")))
            painter.drawText(self.rect(), Qt.AlignCenter, "No data")
            return

        # Draw title
        painter.setPen(QPen(QColor("#1f2937")))
        painter.drawText(10, 20, self.title)

        # Draw current value
        current_value = self.data_points[-1] if self.data_points else 0
        painter.setPen(QPen(self.color))
        painter.drawText(10, 40, f"{current_value:.1f}%")

        # Chart area
        chart_rect = self.rect().adjusted(40, 50, -10, -30)
        if chart_rect.width() <= 0 or chart_rect.height() <= 0:
            return

        # Draw grid lines
        painter.setPen(QPen(QColor("#e5e7eb"), 1))
        for i in range(5):
            y = chart_rect.top() + (chart_rect.height() * i // 4)
            painter.drawLine(chart_rect.left(), y, chart_rect.right(), y)

        # Draw data line
        if len(self.data_points) > 1:
            painter.setPen(QPen(self.color, 2))
            points = list(self.data_points)
            step_x = chart_rect.width() / max(len(points) - 1, 1)

            for i in range(len(points) - 1):
                x1 = chart_rect.left() + int(i * step_x)
                y1 = chart_rect.bottom() - int((points[i] / self.max_value) * chart_rect.height())
                x2 = chart_rect.left() + int((i + 1) * step_x)
                y2 = chart_rect.bottom() - int((points[i + 1] / self.max_value) * chart_rect.height())

                # Clamp y values to chart bounds
                y1 = max(chart_rect.top(), min(chart_rect.bottom(), y1))
                y2 = max(chart_rect.top(), min(chart_rect.bottom(), y2))

                painter.drawLine(x1, y1, x2, y2)

        # Draw y-axis labels
        painter.setPen(QPen(QColor("#6b7280")))
        for i in range(5):
            value = self.max_value * (4 - i) / 4
            y = chart_rect.top() + (chart_rect.height() * i // 4)
            painter.drawText(5, y + 5, f"{value:.0f}")


class ResourceMonitor(QWidget):
    """
    Resource monitor component showing system resource usage.

    Features:
    - CPU usage chart
    - Memory usage chart
    - Disk usage chart
    - Network statistics
    - Real-time updates

    Signals:
        resource_updated: Emitted when resources are updated (cpu, memory, disk)
    """

    resource_updated = Signal(dict)  # {"cpu": float, "memory": float, "disk": float}

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.update_interval = 1000  # 1 second
        self._setup_ui()
        self._setup_update_timer()

    def _setup_ui(self) -> None:
        """Setup the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # Header
        header = QLabel("System Resource Monitor")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #1f2937;")
        layout.addWidget(header)

        if not PSUTIL_AVAILABLE:
            warning = QLabel(
                "⚠️ psutil library not available. Install with: pip install psutil\n"
                "Showing simulated data for demonstration."
            )
            warning.setStyleSheet("color: #f59e0b; background-color: #fef3c7; padding: 8px; border-radius: 4px;")
            warning.setWordWrap(True)
            layout.addWidget(warning)

        # Charts grid
        charts_grid = QGridLayout()
        charts_grid.setSpacing(12)

        # CPU Chart
        self.cpu_chart = MetricChart("CPU Usage", "#3b82f6", 100.0)
        charts_grid.addWidget(self.cpu_chart, 0, 0)

        # Memory Chart
        self.memory_chart = MetricChart("Memory Usage", "#10b981", 100.0)
        charts_grid.addWidget(self.memory_chart, 0, 1)

        # Disk Chart
        self.disk_chart = MetricChart("Disk Usage", "#f59e0b", 100.0)
        charts_grid.addWidget(self.disk_chart, 1, 0)

        # Network info card
        self.network_card = self._create_info_card("Network", "0 KB/s")
        charts_grid.addWidget(self.network_card, 1, 1)

        layout.addLayout(charts_grid)

        # Summary cards
        summary_layout = QHBoxLayout()

        self.cpu_summary = self._create_summary_card("CPU", "0%", "#3b82f6")
        summary_layout.addWidget(self.cpu_summary)

        self.memory_summary = self._create_summary_card("Memory", "0 MB", "#10b981")
        summary_layout.addWidget(self.memory_summary)

        self.disk_summary = self._create_summary_card("Disk", "0 GB", "#f59e0b")
        summary_layout.addWidget(self.disk_summary)

        self.processes_summary = self._create_summary_card("Processes", "0", "#6b7280")
        summary_layout.addWidget(self.processes_summary)

        layout.addLayout(summary_layout)

    def _create_info_card(self, title: str, value: str) -> QWidget:
        """Create an info card widget."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 12px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #374151;")
        layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setStyleSheet("font-size: 20px; color: #1f2937; margin-top: 8px;")
        value_label.setObjectName("network_value")
        layout.addWidget(value_label)

        layout.addStretch()

        return card

    def _create_summary_card(self, title: str, value: str, color: str) -> QWidget:
        """Create a summary card widget."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 6px;
                padding: 12px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: white; font-size: 11px; font-weight: 600;")
        layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold; margin-top: 4px;")
        value_label.setObjectName(f"{title.lower()}_value")
        layout.addWidget(value_label)

        return card

    def _setup_update_timer(self) -> None:
        """Setup periodic update timer."""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.refresh)
        self.update_timer.start(self.update_interval)

    def refresh(self) -> None:
        """Refresh resource usage data."""
        if PSUTIL_AVAILABLE:
            self._update_real_data()
        else:
            self._update_dummy_data()

    def _update_real_data(self) -> None:
        """Update with real system data from psutil."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.cpu_chart.add_data_point(cpu_percent)
            cpu_value_label = self.cpu_summary.findChild(QLabel, "cpu_value")
            if cpu_value_label:
                cpu_value_label.setText(f"{cpu_percent:.1f}%")

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            self.memory_chart.add_data_point(memory_percent)
            memory_value_label = self.memory_summary.findChild(QLabel, "memory_value")
            if memory_value_label:
                memory_mb = memory.used / (1024 * 1024)
                memory_value_label.setText(f"{memory_mb:.0f} MB")

            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            self.disk_chart.add_data_point(disk_percent)
            disk_value_label = self.disk_summary.findChild(QLabel, "disk_value")
            if disk_value_label:
                disk_gb = disk.used / (1024 * 1024 * 1024)
                disk_value_label.setText(f"{disk_gb:.1f} GB")

            # Network
            net_io = psutil.net_io_counters()
            network_value_label = self.network_card.findChild(QLabel, "network_value")
            if network_value_label:
                # Calculate bytes per second (simplified)
                total_mb = (net_io.bytes_sent + net_io.bytes_recv) / (1024 * 1024)
                network_value_label.setText(f"{total_mb:.1f} MB total")

            # Process count
            process_count = len(psutil.pids())
            processes_value_label = self.processes_summary.findChild(QLabel, "processes_value")
            if processes_value_label:
                processes_value_label.setText(str(process_count))

            # Emit signal
            self.resource_updated.emit({
                "cpu": cpu_percent,
                "memory": memory_percent,
                "disk": disk_percent,
            })

        except Exception as e:
            log.error(f"Failed to update resource data: {e}")

    def _update_dummy_data(self) -> None:
        """Update with dummy data for demonstration."""
        import random

        cpu = random.uniform(10, 80)
        memory = random.uniform(30, 70)
        disk = random.uniform(40, 60)

        self.cpu_chart.add_data_point(cpu)
        self.memory_chart.add_data_point(memory)
        self.disk_chart.add_data_point(disk)

        # Update summary cards
        cpu_value_label = self.cpu_summary.findChild(QLabel, "cpu_value")
        if cpu_value_label:
            cpu_value_label.setText(f"{cpu:.1f}%")

        memory_value_label = self.memory_summary.findChild(QLabel, "memory_value")
        if memory_value_label:
            memory_value_label.setText(f"{random.randint(1000, 4000)} MB")

        disk_value_label = self.disk_summary.findChild(QLabel, "disk_value")
        if disk_value_label:
            disk_value_label.setText(f"{random.randint(50, 200)} GB")

        processes_value_label = self.processes_summary.findChild(QLabel, "processes_value")
        if processes_value_label:
            processes_value_label.setText(str(random.randint(100, 300)))

        network_value_label = self.network_card.findChild(QLabel, "network_value")
        if network_value_label:
            network_value_label.setText(f"{random.uniform(0.5, 5.0):.1f} MB total")

        self.resource_updated.emit({
            "cpu": cpu,
            "memory": memory,
            "disk": disk,
        })

    def set_update_interval(self, interval_ms: int) -> None:
        """Set the update interval in milliseconds."""
        self.update_interval = interval_ms
        self.update_timer.setInterval(interval_ms)

    def start_monitoring(self) -> None:
        """Start resource monitoring."""
        if not self.update_timer.isActive():
            self.update_timer.start()

    def stop_monitoring(self) -> None:
        """Stop resource monitoring."""
        self.update_timer.stop()
