"""
Health dashboard for desktop observability.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QProgressBar, QTableWidget, QTableWidgetItem,
    QPushButton, QGroupBox, QGridLayout, QTextEdit
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor
from typing import Dict, Any, List
import psutil
from datetime import datetime


class HealthDashboard(QWidget):
    """
    Desktop observability dashboard.

    Shows:
    - System health (CPU, memory, disk)
    - Execution engine status
    - Scheduler status
    - Recent errors
    - Performance metrics
    """

    export_diagnostics_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.metrics_history: List[Dict[str, Any]] = []

        self._init_ui()
        self._start_monitoring()

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)

        # Header with export button
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h2>System Health Dashboard</h2>"))
        header_layout.addStretch()

        self.export_btn = QPushButton("Export Diagnostics")
        self.export_btn.clicked.connect(self.export_diagnostics_requested.emit)
        header_layout.addWidget(self.export_btn)

        layout.addLayout(header_layout)

        # Top row: System health
        system_group = self._create_system_health_section()
        layout.addWidget(system_group)

        # Middle row: Engine status
        engine_layout = QHBoxLayout()
        engine_layout.addWidget(self._create_execution_engine_section())
        engine_layout.addWidget(self._create_scheduler_section())
        layout.addLayout(engine_layout)

        # Bottom row: Metrics and errors
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self._create_metrics_section())
        bottom_layout.addWidget(self._create_errors_section())
        layout.addLayout(bottom_layout)

    def _create_system_health_section(self) -> QWidget:
        """Create system health monitoring section."""
        group = QGroupBox("System Resources")
        layout = QGridLayout(group)

        # CPU
        layout.addWidget(QLabel("CPU:"), 0, 0)
        self.cpu_progress = QProgressBar()
        self.cpu_progress.setTextVisible(True)
        layout.addWidget(self.cpu_progress, 0, 1)
        self.cpu_label = QLabel("0%")
        layout.addWidget(self.cpu_label, 0, 2)

        # Memory
        layout.addWidget(QLabel("Memory:"), 1, 0)
        self.memory_progress = QProgressBar()
        self.memory_progress.setTextVisible(True)
        layout.addWidget(self.memory_progress, 1, 1)
        self.memory_label = QLabel("0 MB / 0 MB")
        layout.addWidget(self.memory_label, 1, 2)

        # Disk
        layout.addWidget(QLabel("Disk:"), 2, 0)
        self.disk_progress = QProgressBar()
        self.disk_progress.setTextVisible(True)
        layout.addWidget(self.disk_progress, 2, 1)
        self.disk_label = QLabel("0 GB / 0 GB")
        layout.addWidget(self.disk_label, 2, 2)

        # Network (if available)
        layout.addWidget(QLabel("Network:"), 3, 0)
        self.network_label = QLabel("0 KB/s ↓ 0 KB/s ↑")
        layout.addWidget(self.network_label, 3, 1, 1, 2)

        return group

    def _create_execution_engine_section(self) -> QWidget:
        """Create execution engine status section."""
        group = QGroupBox("Execution Engine")
        layout = QVBoxLayout(group)

        # Status
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("Status:"))
        self.engine_status_label = QLabel("Unknown")
        status_layout.addWidget(self.engine_status_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)

        # Stats table
        self.engine_stats_table = QTableWidget()
        self.engine_stats_table.setColumnCount(2)
        self.engine_stats_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.engine_stats_table.horizontalHeader().setStretchLastSection(True)
        self.engine_stats_table.setMaximumHeight(150)
        layout.addWidget(self.engine_stats_table)

        return group

    def _create_scheduler_section(self) -> QWidget:
        """Create scheduler status section."""
        group = QGroupBox("Scheduler")
        layout = QVBoxLayout(group)

        # Status
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("Status:"))
        self.scheduler_status_label = QLabel("Unknown")
        status_layout.addWidget(self.scheduler_status_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)

        # Stats table
        self.scheduler_stats_table = QTableWidget()
        self.scheduler_stats_table.setColumnCount(2)
        self.scheduler_stats_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.scheduler_stats_table.horizontalHeader().setStretchLastSection(True)
        self.scheduler_stats_table.setMaximumHeight(150)
        layout.addWidget(self.scheduler_stats_table)

        return group

    def _create_metrics_section(self) -> QWidget:
        """Create performance metrics section."""
        group = QGroupBox("Performance Metrics")
        layout = QVBoxLayout(group)

        self.metrics_table = QTableWidget()
        self.metrics_table.setColumnCount(3)
        self.metrics_table.setHorizontalHeaderLabels(["Metric", "Current", "Avg"])
        self.metrics_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.metrics_table)

        return group

    def _create_errors_section(self) -> QWidget:
        """Create recent errors section."""
        group = QGroupBox("Recent Errors")
        layout = QVBoxLayout(group)

        self.errors_text = QTextEdit()
        self.errors_text.setReadOnly(True)
        self.errors_text.setMaximumHeight(200)
        layout.addWidget(self.errors_text)

        return group

    def _start_monitoring(self):
        """Start periodic system monitoring."""
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._update_system_metrics)
        self.monitor_timer.start(1000)  # Update every second

    def _update_system_metrics(self):
        """Update system resource metrics."""
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        self.cpu_progress.setValue(int(cpu_percent))
        self.cpu_label.setText(f"{cpu_percent:.1f}%")

        if cpu_percent > 80:
            self.cpu_progress.setStyleSheet("QProgressBar::chunk { background-color: red; }")
        elif cpu_percent > 60:
            self.cpu_progress.setStyleSheet("QProgressBar::chunk { background-color: orange; }")
        else:
            self.cpu_progress.setStyleSheet("QProgressBar::chunk { background-color: green; }")

        # Memory
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_mb = memory.used / (1024 ** 2)
        memory_total_mb = memory.total / (1024 ** 2)

        self.memory_progress.setValue(int(memory_percent))
        self.memory_label.setText(f"{memory_used_mb:.0f} MB / {memory_total_mb:.0f} MB")

        if memory_percent > 80:
            self.memory_progress.setStyleSheet("QProgressBar::chunk { background-color: red; }")
        elif memory_percent > 60:
            self.memory_progress.setStyleSheet("QProgressBar::chunk { background-color: orange; }")
        else:
            self.memory_progress.setStyleSheet("QProgressBar::chunk { background-color: green; }")

        # Disk
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_used_gb = disk.used / (1024 ** 3)
        disk_total_gb = disk.total / (1024 ** 3)

        self.disk_progress.setValue(int(disk_percent))
        self.disk_label.setText(f"{disk_used_gb:.1f} GB / {disk_total_gb:.1f} GB")

        if disk_percent > 90:
            self.disk_progress.setStyleSheet("QProgressBar::chunk { background-color: red; }")
        elif disk_percent > 75:
            self.disk_progress.setStyleSheet("QProgressBar::chunk { background-color: orange; }")
        else:
            self.disk_progress.setStyleSheet("QProgressBar::chunk { background-color: green; }")

        # Network
        try:
            net_io = psutil.net_io_counters()
            if hasattr(self, '_prev_net_io'):
                bytes_sent = net_io.bytes_sent - self._prev_net_io.bytes_sent
                bytes_recv = net_io.bytes_recv - self._prev_net_io.bytes_recv
                self.network_label.setText(
                    f"{bytes_recv / 1024:.1f} KB/s ↓ {bytes_sent / 1024:.1f} KB/s ↑"
                )
            self._prev_net_io = net_io
        except:
            self.network_label.setText("N/A")

        # Store metrics
        self.metrics_history.append({
            'timestamp': datetime.utcnow().isoformat(),
            'cpu_percent': cpu_percent,
            'memory_percent': memory_percent,
            'disk_percent': disk_percent
        })

        # Keep only last 60 samples (1 minute)
        if len(self.metrics_history) > 60:
            self.metrics_history.pop(0)

    def update_engine_status(self, stats: Dict[str, Any]):
        """
        Update execution engine status.

        Args:
            stats: Engine statistics from CoreExecutionEngine.get_stats()
        """
        # Status indicator
        is_running = stats.get('is_running', False)
        self.engine_status_label.setText("Running" if is_running else "Stopped")
        self.engine_status_label.setStyleSheet(
            f"color: {'green' if is_running else 'red'}; font-weight: bold;"
        )

        # Stats table
        metrics = [
            ("Total Executions", stats.get('total_executions', 0)),
            ("Active Executions", stats.get('active_executions', 0)),
            ("Running", stats.get('by_state', {}).get('RUNNING', 0)),
            ("Paused", stats.get('by_state', {}).get('PAUSED', 0)),
            ("Completed", stats.get('by_state', {}).get('COMPLETED', 0)),
            ("Failed", stats.get('by_state', {}).get('FAILED', 0)),
        ]

        self.engine_stats_table.setRowCount(len(metrics))
        for row, (metric, value) in enumerate(metrics):
            self.engine_stats_table.setItem(row, 0, QTableWidgetItem(metric))
            self.engine_stats_table.setItem(row, 1, QTableWidgetItem(str(value)))

    def update_scheduler_status(self, stats: Dict[str, Any]):
        """
        Update scheduler status.

        Args:
            stats: Scheduler statistics from DesktopScheduler.get_stats()
        """
        # Status indicator
        is_running = stats.get('is_running', False)
        self.scheduler_status_label.setText("Running" if is_running else "Stopped")
        self.scheduler_status_label.setStyleSheet(
            f"color: {'green' if is_running else 'red'}; font-weight: bold;"
        )

        # Stats table
        metrics = [
            ("Total Jobs", stats.get('total_jobs', 0)),
            ("Enabled Jobs", stats.get('enabled_jobs', 0)),
            ("Total Runs", stats.get('total_runs', 0)),
            ("Next Run", stats.get('next_run_time', 'N/A')),
        ]

        self.scheduler_stats_table.setRowCount(len(metrics))
        for row, (metric, value) in enumerate(metrics):
            self.scheduler_stats_table.setItem(row, 0, QTableWidgetItem(metric))
            self.scheduler_stats_table.setItem(row, 1, QTableWidgetItem(str(value)))

    def update_performance_metrics(self, metrics: Dict[str, Any]):
        """
        Update performance metrics.

        Args:
            metrics: Performance metrics dict
        """
        metric_items = [
            ("Avg Execution Time", f"{metrics.get('avg_execution_time_seconds', 0):.2f}s"),
            ("Success Rate", f"{metrics.get('success_rate_percent', 0):.1f}%"),
            ("Total Data Processed", f"{metrics.get('total_data_processed_mb', 0):.1f} MB"),
        ]

        self.metrics_table.setRowCount(len(metric_items))
        for row, (metric, value) in enumerate(metric_items):
            self.metrics_table.setItem(row, 0, QTableWidgetItem(metric))
            self.metrics_table.setItem(row, 1, QTableWidgetItem(value))
            # TODO: Calculate average over time
            self.metrics_table.setItem(row, 2, QTableWidgetItem(value))

    def add_error(self, error_msg: str, timestamp: datetime = None):
        """
        Add error to recent errors list.

        Args:
            error_msg: Error message
            timestamp: Error timestamp (default: now)
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        current_text = self.errors_text.toPlainText()
        new_entry = f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {error_msg}\n"

        # Prepend new error
        self.errors_text.setPlainText(new_entry + current_text)

        # Keep only last 20 errors
        lines = self.errors_text.toPlainText().split('\n')
        if len(lines) > 20:
            self.errors_text.setPlainText('\n'.join(lines[:20]))

    def get_system_snapshot(self) -> Dict[str, Any]:
        """
        Get current system health snapshot.

        Returns:
            Dict with system metrics
        """
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            'timestamp': datetime.utcnow().isoformat(),
            'cpu': {
                'percent': cpu_percent,
                'count': psutil.cpu_count()
            },
            'memory': {
                'percent': memory.percent,
                'used_mb': memory.used / (1024 ** 2),
                'total_mb': memory.total / (1024 ** 2)
            },
            'disk': {
                'percent': disk.percent,
                'used_gb': disk.used / (1024 ** 3),
                'total_gb': disk.total / (1024 ** 3)
            },
            'metrics_history': self.metrics_history.copy()
        }


class MetricsVisualization(QWidget):
    """
    Time-series visualization of metrics.

    Shows CPU, memory, disk usage over time.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_points: List[Dict[str, Any]] = []
        self.max_points = 60  # 1 minute at 1Hz

        self._init_ui()

    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h3>Resource Usage (Last 60s)</h3>"))

        # Simple text-based visualization (can be replaced with proper charts)
        self.viz_text = QTextEdit()
        self.viz_text.setReadOnly(True)
        self.viz_text.setFontFamily("Courier")
        layout.addWidget(self.viz_text)

        # Update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_visualization)
        self.timer.start(1000)

    def add_data_point(self, cpu: float, memory: float, disk: float):
        """Add data point."""
        self.data_points.append({
            'timestamp': datetime.utcnow(),
            'cpu': cpu,
            'memory': memory,
            'disk': disk
        })

        if len(self.data_points) > self.max_points:
            self.data_points.pop(0)

    def _update_visualization(self):
        """Update ASCII visualization."""
        if not self.data_points:
            return

        lines = []
        lines.append("CPU Usage:")
        lines.append(self._create_sparkline([p['cpu'] for p in self.data_points]))
        lines.append("")

        lines.append("Memory Usage:")
        lines.append(self._create_sparkline([p['memory'] for p in self.data_points]))
        lines.append("")

        lines.append("Disk Usage:")
        lines.append(self._create_sparkline([p['disk'] for p in self.data_points]))

        self.viz_text.setPlainText('\n'.join(lines))

    def _create_sparkline(self, values: List[float]) -> str:
        """Create ASCII sparkline."""
        if not values:
            return ""

        chars = " ▁▂▃▄▅▆▇█"
        max_val = max(values) if values else 1

        sparkline = ""
        for val in values[-60:]:  # Last 60 points
            idx = min(int((val / 100) * len(chars)), len(chars) - 1)
            sparkline += chars[idx]

        return sparkline + f"  {values[-1]:.1f}%"
