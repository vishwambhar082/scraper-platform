"""
Refactored main window with execution engine integration.

This replaces polling with event-driven architecture and uses CoreExecutionEngine.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QThread, Signal, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QIcon, QKeySequence, QDesktopServices, QColor
from PySide6.QtWidgets import *
from PySide6.QtWebEngineWidgets import QWebEngineView

from src.common.logging_utils import get_logger
from src.ui.workflow_graph import WorkflowGraphWidget
from src.ui.theme import ThemeManager
from src.ui.airflow_service import AirflowServiceManager
from src.ui.path_utils import open_path, open_parent_folder
from src.ui.modern_components import (
    IconSidebar, Card, ActivityCard, SectionHeader,
    BulletList, ActivityPanel
)
from src.ui.diagnostics_dialog import DiagnosticsDialog

# Import new execution system
from execution import CoreExecutionEngine, ExecutionState
from scheduler import DesktopScheduler, ScheduleConfig
from ui.state import AppStore, AppState, Action, ActionType, EventBus
from ui.app_integration import ExecutionIntegration

log = get_logger("ui.main_window")


class MainWindow(QMainWindow):
    """Refactored main window with event-driven execution."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scraper Platform")
        self.resize(1400, 900)

        # Theme
        self.theme_manager = ThemeManager()
        self._apply_theme("light")

        # Airflow (legacy, will be replaced)
        self.airflow_service = AirflowServiceManager()
        self.airflow_auto_start = False

        # NEW: Event-driven state management
        self.store = AppStore()
        self.event_bus = EventBus()

        # NEW: Execution integration (replaces JobManager + polling)
        self.integration = ExecutionIntegration(self.store, self.event_bus)

        # Legacy state (will migrate to store)
        self.event_history: List[Dict[str, Any]] = []
        self.run_history: List[Any] = []
        self._last_history_refresh: datetime | None = None
        self.log_buffer: List[Dict[str, Any]] = []
        self.logs_autoscroll = True
        self.log_file_path = Path("logs/ui_logs.json")

        # Setup UI
        self._setup_ui()
        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_status_bar()
        self.menuBar().setVisible(False)
        if hasattr(self, "toolbar"):
            self.toolbar.setVisible(False)

        # Setup logging
        self._setup_logging()

        # Wire event bus to UI updates
        self._wire_event_bus()

        # Start integration
        self.integration.start()

        # Load initial data
        self._refresh_run_history()

        # NO MORE POLLING - event-driven updates only
        # self.update_timer.start(2000)  # DELETED

    def _wire_event_bus(self):
        """Wire event bus signals to UI update handlers."""
        self.event_bus.job_state_changed.connect(self._on_job_state_changed)
        self.event_bus.log_received.connect(self._on_log_received)
        self.event_bus.error_occurred.connect(self._on_error_occurred)
        self.event_bus.progress_updated.connect(self._on_progress_updated)

    def _on_job_state_changed(self, job_id: str, state: Any):
        """Handle job state change (event-driven)."""
        log.info(f"Job {job_id} state changed to {state}")
        self._update_job_display(job_id, state)

    def _on_log_received(self, job_id: str, level: str, message: str):
        """Handle log message (event-driven)."""
        self._append_console(f"[{level}] {message}")

    def _on_error_occurred(self, job_id: str, error: str):
        """Handle error (event-driven)."""
        QMessageBox.critical(self, "Job Error", f"Job {job_id} failed:\n{error}")

    def _on_progress_updated(self, job_id: str, progress: float, current_step: str):
        """Handle progress update (event-driven)."""
        self._update_progress_bar(job_id, progress, current_step)

    def _start_job(self):
        """Start job via execution engine (NOT JobManager)."""
        source = self.source_combo.currentText()
        run_type = self.run_type_combo.currentText()
        environment = self.env_combo.currentText()

        try:
            # Use integration instead of JobManager
            run_id = self.integration.start_job(
                source=source,
                run_type=run_type,
                environment=environment
            )

            log.info(f"Started job: {run_id}")
            self._append_console(f"Started job: {run_id}")

            # State updates happen via events, not polling

        except Exception as e:
            log.error(f"Failed to start job: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start job:\n{e}")

    def _pause_job(self, job_id: str):
        """Pause job via execution engine."""
        success = self.integration.pause_job(job_id)
        if success:
            self._append_console(f"Paused job: {job_id}")
        else:
            self._append_console(f"Failed to pause job: {job_id}")

    def _resume_job(self, job_id: str):
        """Resume job via execution engine."""
        success = self.integration.resume_job(job_id)
        if success:
            self._append_console(f"Resumed job: {job_id}")
        else:
            self._append_console(f"Failed to resume job: {job_id}")

    def _stop_job(self, job_id: str):
        """Stop job via execution engine."""
        success = self.integration.stop_job(job_id)
        if success:
            self._append_console(f"Stopped job: {job_id}")
        else:
            self._append_console(f"Failed to stop job: {job_id}")

    def _update_job_display(self, job_id: str, state: Any):
        """Update job display in UI."""
        # Find job in list and update visual state
        if hasattr(self, 'job_list'):
            for i in range(self.job_list.count()):
                item = self.job_list.item(i)
                if item and item.data(Qt.UserRole) == job_id:
                    item.setText(f"{job_id} - {state}")
                    # Update color based on state
                    if state == 'running':
                        item.setForeground(QColor('#FFA500'))
                    elif state == 'completed':
                        item.setForeground(QColor('#00FF00'))
                    elif state == 'failed':
                        item.setForeground(QColor('#FF0000'))
                    elif state == 'paused':
                        item.setForeground(QColor('#FFFF00'))

    def _update_progress_bar(self, job_id: str, progress: float, current_step: str):
        """Update progress bar for job."""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(int(progress * 100))
            if hasattr(self, 'progress_label'):
                self.progress_label.setText(f"{current_step} - {progress*100:.0f}%")

    def _append_console(self, message: str):
        """Append message to console output."""
        if hasattr(self, 'console_output'):
            self.console_output.append(message)
            if self.logs_autoscroll:
                cursor = self.console_output.textCursor()
                cursor.movePosition(cursor.End)
                self.console_output.setTextCursor(cursor)

    def _setup_ui(self):
        """Setup main UI."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Top controls
        controls = self._create_controls()
        layout.addWidget(controls)

        # Main content (splitter)
        splitter = QSplitter(Qt.Vertical)

        # Job list and details
        top_widget = self._create_job_panel()
        splitter.addWidget(top_widget)

        # Console output
        console_widget = self._create_console_panel()
        splitter.addWidget(console_widget)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

    def _create_controls(self) -> QWidget:
        """Create top control panel."""
        widget = QWidget()
        layout = QHBoxLayout(widget)

        # Source selection
        layout.addWidget(QLabel("Source:"))
        self.source_combo = QComboBox()
        self.source_combo.addItems(['alfabeta', 'quebec', 'lafa', 'chile', 'argentina'])
        layout.addWidget(self.source_combo)

        # Run type
        layout.addWidget(QLabel("Run Type:"))
        self.run_type_combo = QComboBox()
        self.run_type_combo.addItems(['FULL_REFRESH', 'DELTA', 'SINGLE_PRODUCT'])
        layout.addWidget(self.run_type_combo)

        # Environment
        layout.addWidget(QLabel("Environment:"))
        self.env_combo = QComboBox()
        self.env_combo.addItems(['dev', 'staging', 'prod'])
        layout.addWidget(self.env_combo)

        # Start button
        start_btn = QPushButton("Start Job")
        start_btn.clicked.connect(self._start_job)
        layout.addWidget(start_btn)

        layout.addStretch()

        return widget

    def _create_job_panel(self) -> QWidget:
        """Create job list and details panel."""
        widget = QWidget()
        layout = QHBoxLayout(widget)

        # Left: Job list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("Active Jobs"))

        self.job_list = QListWidget()
        self.job_list.itemClicked.connect(self._on_job_selected)
        left_layout.addWidget(self.job_list)

        # Job controls
        controls = QHBoxLayout()
        pause_btn = QPushButton("Pause")
        pause_btn.clicked.connect(lambda: self._pause_job(self._get_selected_job()))
        controls.addWidget(pause_btn)

        resume_btn = QPushButton("Resume")
        resume_btn.clicked.connect(lambda: self._resume_job(self._get_selected_job()))
        controls.addWidget(resume_btn)

        stop_btn = QPushButton("Stop")
        stop_btn.clicked.connect(lambda: self._stop_job(self._get_selected_job()))
        controls.addWidget(stop_btn)

        left_layout.addLayout(controls)
        layout.addWidget(left_panel)

        # Right: Job details
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(QLabel("Job Details"))

        self.job_details = QTextEdit()
        self.job_details.setReadOnly(True)
        right_layout.addWidget(self.job_details)

        # Progress
        self.progress_label = QLabel("Progress: 0%")
        right_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        right_layout.addWidget(self.progress_bar)

        layout.addWidget(right_panel)

        return widget

    def _create_console_panel(self) -> QWidget:
        """Create console output panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        header = QHBoxLayout()
        header.addWidget(QLabel("Console Output"))

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(lambda: self.console_output.clear())
        header.addWidget(clear_btn)

        autoscroll_cb = QCheckBox("Auto-scroll")
        autoscroll_cb.setChecked(True)
        autoscroll_cb.toggled.connect(lambda checked: setattr(self, 'logs_autoscroll', checked))
        header.addWidget(autoscroll_cb)

        header.addStretch()
        layout.addLayout(header)

        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: 'Consolas';")
        layout.addWidget(self.console_output)

        return widget

    def _on_job_selected(self, item):
        """Handle job selection."""
        job_id = item.data(Qt.UserRole)
        status = self.integration.get_job_status(job_id)

        if status:
            details = f"""
Job ID: {status.run_id}
Pipeline: {status.pipeline_id}
Source: {status.source}
State: {status.state.value}
Progress: {status.progress * 100:.1f}%
Current Step: {status.current_step or 'N/A'}
Completed: {status.completed_steps}/{status.total_steps}
Started: {status.started_at}
Error: {status.error or 'None'}
            """
            self.job_details.setText(details.strip())

    def _get_selected_job(self) -> str:
        """Get currently selected job ID."""
        items = self.job_list.selectedItems()
        if items:
            return items[0].data(Qt.UserRole)
        return ""

    def _refresh_job_list(self):
        """Refresh job list from execution engine."""
        self.job_list.clear()

        active_jobs = self.integration.get_active_jobs()
        for ctx in active_jobs:
            item = QListWidgetItem(f"{ctx.run_id} - {ctx.state.value}")
            item.setData(Qt.UserRole, ctx.run_id)
            self.job_list.addItem(item)

    def _refresh_run_history(self):
        """Refresh run history (legacy, keep for now)."""
        pass

    def _setup_menu_bar(self):
        """Setup menu bar."""
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _setup_toolbar(self):
        """Setup toolbar."""
        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)

    def _setup_status_bar(self):
        """Setup status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _setup_logging(self):
        """Setup UI logging handler."""
        from src.ui.logging_handler import UILoggingHandler
        handler = UILoggingHandler()
        handler.log_message.connect(lambda level, msg: self._append_console(f"[{level}] {msg}"))

    def _apply_theme(self, theme: str):
        """Apply theme to UI."""
        if theme == "light":
            self.setStyleSheet("QMainWindow { background-color: #ffffff; }")
        else:
            self.setStyleSheet("QMainWindow { background-color: #2b2b2b; }")

    def closeEvent(self, event):
        """Handle window close."""
        # Shutdown execution integration
        self.integration.shutdown()

        # Shutdown Airflow
        if self.airflow_service:
            self.airflow_service.stop_airflow()

        event.accept()


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
