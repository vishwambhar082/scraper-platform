"""
Job Dashboard Component.

Provides a comprehensive view of running and historical jobs including:
- Job list/grid view
- Job status indicators with color coding
- Job controls (start/stop/pause)
- Real-time updates of job status
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from PySide6.QtCore import Signal, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QComboBox,
    QLabel,
    QMessageBox,
)

from src.common.logging_utils import get_logger
from src.ui.job_manager import JobManager

log = get_logger("ui.components.dashboard")


class JobDashboard(QWidget):
    """
    Job dashboard component showing active and historical jobs.

    Features:
    - Job list table with sortable columns
    - Start/stop job controls
    - Real-time status updates
    - Detailed job information on selection

    Signals:
        job_started: Emitted when a job is started
        job_stopped: Emitted when a job is stopped
        job_selected: Emitted when a job is selected (job_id)
    """

    job_started = Signal(str)  # job_id
    job_stopped = Signal(str)  # job_id
    job_selected = Signal(str)  # job_id

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.job_manager = JobManager()
        self._setup_ui()
        self._setup_update_timer()

    def _setup_ui(self) -> None:
        """Setup the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Controls section
        controls = self._create_controls()
        layout.addLayout(controls)

        # Jobs table
        self.jobs_table = self._create_jobs_table()
        layout.addWidget(self.jobs_table, 1)

    def _create_controls(self) -> QGridLayout:
        """Create the job control panel."""
        controls = QGridLayout()
        controls.setSpacing(8)

        # Row 1: Source and Run Type
        controls.addWidget(QLabel("Source:"), 0, 0)
        self.source_combo = QComboBox()
        self.source_combo.addItems(["alfabeta", "argentina", "chile", "lafa", "quebec", "template"])
        self.source_combo.setMinimumWidth(150)
        controls.addWidget(self.source_combo, 0, 1)

        controls.addWidget(QLabel("Run Type:"), 0, 2)
        self.run_type_combo = QComboBox()
        self.run_type_combo.addItems(["FULL_REFRESH", "DELTA", "SINGLE_PRODUCT"])
        self.run_type_combo.setMinimumWidth(150)
        controls.addWidget(self.run_type_combo, 0, 3)

        # Row 2: Environment and Action Buttons
        controls.addWidget(QLabel("Environment:"), 1, 0)
        self.env_combo = QComboBox()
        self.env_combo.addItems(["dev", "staging", "prod"])
        self.env_combo.setMinimumWidth(150)
        controls.addWidget(self.env_combo, 1, 1)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(6)

        self.start_btn = QPushButton("Start Job")
        self.start_btn.setProperty("class", "success")
        self.start_btn.clicked.connect(self._start_job)
        self.start_btn.setMinimumWidth(100)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:disabled {
                background-color: #9ca3af;
            }
        """)
        button_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Stop Job")
        self.stop_btn.setProperty("class", "danger")
        self.stop_btn.clicked.connect(self._stop_job)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setMinimumWidth(100)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                border: none;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
            QPushButton:disabled {
                background-color: #9ca3af;
            }
        """)
        button_layout.addWidget(self.stop_btn)

        button_layout.addStretch()
        controls.addLayout(button_layout, 1, 2, 1, 2)

        return controls

    def _create_jobs_table(self) -> QTableWidget:
        """Create the jobs table."""
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "Run ID", "Source", "Status", "Started", "Duration", "Items"
        ])
        table.horizontalHeader().setStretchLastSection(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        table.itemSelectionChanged.connect(self._on_job_selected)
        table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e5e7eb;
                border: 1px solid #e5e7eb;
                border-radius: 4px;
            }
            QHeaderView::section {
                background-color: #f3f4f6;
                padding: 8px;
                border: 1px solid #e5e7eb;
                font-weight: 600;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #dbeafe;
                color: #1e3a8a;
            }
        """)
        return table

    def _setup_update_timer(self) -> None:
        """Setup periodic update timer."""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.refresh)
        self.update_timer.start(2000)  # Update every 2 seconds

    def _start_job(self) -> None:
        """Start a new job."""
        source = self.source_combo.currentText()
        run_type = self.run_type_combo.currentText()
        environment = self.env_combo.currentText()
        job_id = f"{source}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

        try:
            self.job_manager.start_job(
                job_id,
                source=source,
                run_type=run_type,
                environment=environment
            )
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.job_started.emit(job_id)
            log.info(f"Started job: {job_id}")
        except Exception as e:
            log.error(f"Failed to start job: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start job: {e}")

    def _stop_job(self) -> None:
        """Stop the selected job."""
        row = self.jobs_table.currentRow()
        if row >= 0:
            job_id = self.jobs_table.item(row, 0).text()
            try:
                self.job_manager.stop_job(job_id)
                self.job_stopped.emit(job_id)
                log.info(f"Stopped job: {job_id}")
            except Exception as e:
                log.error(f"Failed to stop job: {e}")
                QMessageBox.critical(self, "Error", f"Failed to stop job: {e}")

    def _on_job_selected(self) -> None:
        """Handle job selection."""
        row = self.jobs_table.currentRow()
        if row >= 0:
            job_id = self.jobs_table.item(row, 0).text()
            self.job_selected.emit(job_id)

    def refresh(self) -> None:
        """Refresh the job list."""
        try:
            jobs = self.job_manager.list_jobs()
            rows = list(jobs.values())

            self.jobs_table.setRowCount(len(rows))
            for i, info in enumerate(rows):
                # Run ID
                self.jobs_table.setItem(i, 0, QTableWidgetItem(info.job_id))

                # Source
                self.jobs_table.setItem(i, 1, QTableWidgetItem(info.source))

                # Status with color coding
                status_item = QTableWidgetItem(info.status)
                status_item.setBackground(QColor(self._status_color(info.status)))
                status_item.setForeground(QColor("#ffffff"))
                self.jobs_table.setItem(i, 2, status_item)

                # Started time
                started = datetime.fromtimestamp(info.started_at) if info.started_at else None
                started_str = started.strftime("%Y-%m-%d %H:%M:%S") if started else "-"
                self.jobs_table.setItem(i, 3, QTableWidgetItem(started_str))

                # Duration
                duration = ""
                if info.started_at and info.ended_at:
                    duration = f"{int(info.ended_at - info.started_at)}s"
                elif info.started_at:
                    duration = f"{int(datetime.utcnow().timestamp() - info.started_at)}s"
                self.jobs_table.setItem(i, 4, QTableWidgetItem(duration))

                # Items count
                items_val = info.result.get("item_count") if info.result else ""
                self.jobs_table.setItem(i, 5, QTableWidgetItem(str(items_val) if items_val else "-"))

            # Auto-select first row if none selected
            if rows and self.jobs_table.currentRow() < 0:
                self.jobs_table.selectRow(0)

            # Update button states
            all_done = all(info.status in ("completed", "failed", "stopped") for info in rows)
            if all_done or not rows:
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)

        except Exception as e:
            log.error(f"Failed to refresh job list: {e}")

    def _status_color(self, status: str) -> str:
        """Get color for status."""
        colors = {
            "running": "#3b82f6",
            "completed": "#10b981",
            "failed": "#ef4444",
            "stopped": "#f59e0b",
            "pending": "#6b7280",
        }
        return colors.get(status, "#6b7280")

    def get_selected_job_id(self) -> Optional[str]:
        """Get the currently selected job ID."""
        row = self.jobs_table.currentRow()
        if row >= 0:
            return self.jobs_table.item(row, 0).text()
        return None

    def get_job_info(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific job."""
        return self.job_manager.jobs.get(job_id)
