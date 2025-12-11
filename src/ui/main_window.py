"""
Main window for the Scraper Platform Desktop Application.

This module provides a comprehensive desktop UI with:
- Left pane: Job list, tasks, logs, execution history
- Right pane: Real-time workflow graph, Airflow DAG view, status indicators
- Bottom panel: Live console output
- Unified event history with search/filter
- Dark/light theme support
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from cryptography.fernet import Fernet
from PySide6.QtCore import QThread, Signal, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QIcon, QKeySequence, QDesktopServices, QColor
from PySide6.QtWidgets import QStyle
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QTextEdit,
    QLabel,
    QPushButton,
    QComboBox,
    QCheckBox,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTabWidget,
    QMessageBox,
    QFileDialog,
    QStatusBar,
    QMenuBar,
    QMenu,
    QToolBar,
    QProgressBar,
    QStackedWidget,
    QButtonGroup,
    QFrame,
    QListWidget,
    QListWidgetItem,
    QTextBrowser,
    QSizePolicy,
    QGroupBox,
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from src.common.logging_utils import get_logger
from src.entrypoints.run_pipeline import run_pipeline
from src.pipeline import PipelineCompiler, UnifiedRegistry
from src.run_tracking.recorder import RunRecorder
from src.scheduler import scheduler_db_adapter as run_db
from src.security.crypto_utils import _DEFAULT_KEY_PATH
from src.ui.logging_handler import UILoggingHandler
from src.ui.workflow_graph import WorkflowGraphWidget
from src.ui.theme import ThemeManager
from src.ui.airflow_service import AirflowServiceManager
from src.ui.airflow_service_thread import AirflowServiceStartThread
from src.ui.job_manager import JobManager
from src.ui.path_utils import open_path, open_parent_folder

log = get_logger("ui.main_window")


class PipelineRunnerThread(QThread):
    """Thread for running pipelines without blocking the UI."""
    
    finished = Signal(dict)  # Emits run result
    log_message = Signal(str, str)  # Emits (level, message)
    step_progress = Signal(str, str)  # Emits (step_id, status)
    
    def __init__(
        self,
        source: str,
        run_type: str = "FULL_REFRESH",
        environment: str = "dev",
        params: Optional[Dict[str, Any]] = None,
    ):
        super().__init__()
        self.source = source
        self.run_type = run_type
        self.environment = environment
        self.params = params or {}
        self._cancelled = False
    
    def cancel(self) -> None:
        """Cancel the pipeline execution."""
        self._cancelled = True
    
    def run(self) -> None:
        """Execute the pipeline in the background thread."""
        try:
            self.log_message.emit("INFO", f"Starting pipeline: {self.source}")
            result = run_pipeline(
                source=self.source,
                run_type=self.run_type,
                environment=self.environment,
                params=self.params,
            )
            self.finished.emit(result)
        except Exception as e:
            self.log_message.emit("ERROR", f"Pipeline failed: {str(e)}")
            self.finished.emit({"status": "failed", "error": str(e)})


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Scraper Platform - Desktop Application")
        self.setGeometry(100, 100, 1400, 900)
        # Set window icon if available
        # self.setWindowIcon(QIcon("path/to/icon.png"))
        # Improve overall styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1d26;
            }
            QLabel {
                color: #e8e8e8;
            }
            QPushButton {
                background-color: #2d3650;
                color: #cfd8e3;
                border: 1px solid #444c66;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #3a4567;
                border-color: #4f79ff;
            }
            QPushButton:pressed {
                background-color: #252d45;
            }
            QPushButton:disabled {
                background-color: #2a2d3a;
                color: #6c757d;
                border-color: #3a3f4b;
            }
            QComboBox {
                background-color: #2d3650;
                color: #e8e8e8;
                border: 1px solid #444c66;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QComboBox:hover {
                border-color: #4f79ff;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2d3650;
                color: #e8e8e8;
                border: 1px solid #444c66;
                selection-background-color: #4f79ff;
            }
            QLineEdit {
                background-color: #2d3650;
                color: #e8e8e8;
                border: 1px solid #444c66;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QLineEdit:focus {
                border-color: #4f79ff;
            }
            QTextEdit, QPlainTextEdit {
                background-color: #1c212d;
                color: #e8e8e8;
                border: 1px solid #2f3744;
                border-radius: 4px;
            }
            QTabWidget::pane {
                border: 1px solid #2f3744;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #2d3650;
                color: #cfd8e3;
                border: 1px solid #2f3744;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #4f79ff;
                color: white;
                border-color: #4f79ff;
            }
            QTabBar::tab:hover:!selected {
                background-color: #3a4567;
            }
        """)
        
        # Theme manager
        self.theme_manager = ThemeManager()
        self._apply_theme("dark")  # Start with dark theme
        
        # Airflow service manager
        self.airflow_service = AirflowServiceManager()
        self.airflow_auto_start = False  # Will be configurable
        self.airflow_start_thread: Optional[AirflowServiceStartThread] = None
        
        # State
        self.current_jobs: Dict[str, Dict[str, Any]] = {}
        self.event_history: List[Dict[str, Any]] = []
        self.run_history: List[Any] = []
        self._last_history_refresh: datetime | None = None
        self.pipeline_runner: Optional[PipelineRunnerThread] = None
        self.setup_snapshot: Dict[str, Any] = {}
        self.job_manager = JobManager()
        self.log_buffer: List[Dict[str, Any]] = []
        self.logs_autoscroll = True
        self.history_page = 0
        self.history_page_size = 15
        
        # Setup UI
        self.setup_snapshot = self._auto_initialize_environment()
        self._setup_ui()
        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_status_bar()
        # Hide traditional menu/toolbar for a cleaner, page-based nav
        self.menuBar().setVisible(False)
        if hasattr(self, "toolbar"):
            self.toolbar.setVisible(False)
        
        # Setup logging handler
        self._setup_logging()
        
        # Load initial data
        self._refresh_job_list()
        self._load_event_history()
        self._refresh_run_history()
        
        # Timer for periodic updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._periodic_update)
        self.update_timer.start(2000)  # Update every 2 seconds
    
    def _create_console_panel(self) -> QWidget:
        """Create a reusable console panel widget."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Console header
        header = QHBoxLayout()
        header.addWidget(QLabel("Console Output"))
        header.addStretch()
        
        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet("padding: 2px 8px; font-size: 12px;")
        clear_btn.clicked.connect(lambda: self.console_output.clear())
        header.addWidget(clear_btn)
        
        # Auto-scroll checkbox
        self.console_autoscroll_cb = QCheckBox("Auto-scroll")
        self.console_autoscroll_cb.setChecked(True)
        self.console_autoscroll_cb.stateChanged.connect(self._toggle_console_autoscroll)
        header.addWidget(self.console_autoscroll_cb)
        
        layout.addLayout(header)
        
        # Console output area
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setStyleSheet("""
            QTextEdit {
                background-color: #1c212d;
                color: #e8e8e8;
                border: 1px solid #2f3744;
                border-radius: 4px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.console_output, 1)
        
        return panel

    def _setup_ui(self) -> None:
        """Setup the main UI layout with vertical nav + main content + console."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main horizontal layout: nav | content | console
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Sidebar navigation
        nav_widget = QWidget()
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(12)
        nav_widget.setFixedWidth(180)  # Fixed width for navigation

        # Navigation title
        nav_title = QLabel("Navigation")
        nav_title.setStyleSheet("font-size: 16px; font-weight: 600; color: #cfd8e3; padding: 10px 0;")
        nav_layout.addWidget(nav_title)

        self.nav_buttons = QButtonGroup(self)
        self.nav_buttons.setExclusive(True)

        self.nav_runs_btn = self._styled_nav_button("Runs & Jobs", checked=True, on_click=lambda: self._switch_page(0))
        nav_layout.addWidget(self.nav_runs_btn)

        self.nav_workflow_btn = self._styled_nav_button("Workflow / Airflow", on_click=lambda: self._switch_page(1))
        nav_layout.addWidget(self.nav_workflow_btn)

        self.nav_setup_btn = self._styled_nav_button("Setup & Settings", on_click=lambda: self._switch_page(2))
        nav_layout.addWidget(self.nav_setup_btn)

        nav_layout.addStretch()
        
        # Add a footer with version info
        version_label = QLabel("v5.0")
        version_label.setStyleSheet("color: #6c757d; font-size: 12px; padding: 5px;")
        nav_layout.addWidget(version_label)
        
        main_layout.addWidget(nav_widget)

        # Middle content area - Stacked widgets for different pages
        content_stack = QWidget()
        content_layout = QVBoxLayout(content_stack)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        self.main_stack = QStackedWidget()
        runs_console_page = self._create_runs_console_page()
        workflow_page = self._create_workflow_status_page()
        setup_page = self._create_setup_page()
        self.main_stack.addWidget(runs_console_page)
        self.main_stack.addWidget(workflow_page)
        self.main_stack.addWidget(setup_page)
        
        content_layout.addWidget(self.main_stack, 1)
        main_layout.addWidget(content_stack, 1)  # Middle section takes remaining space
        
        # Right side console panel (always visible)
        console_panel = self._create_console_panel()
        main_layout.addWidget(console_panel, 1)  # Console takes 1/3 of the width
    
    def _create_left_pane(self) -> QWidget:
        """Create the left pane with job list, tasks, logs, history."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Tabs for different views
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #2f3744;
                border-radius: 8px;
                padding: 5px;
            }
            QTabBar::tab {
                background-color: #2d3650;
                color: #cfd8e3;
                border: 1px solid #2f3744;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 16px;
                margin-right: 2px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background-color: #4f79ff;
                color: white;
                border-color: #4f79ff;
            }
            QTabBar::tab:hover:!selected {
                background-color: #3a4567;
            }
        """)
        
        # Jobs tab
        jobs_tab = self._create_jobs_tab()
        tabs.addTab(jobs_tab, "Jobs")
        
        # Tasks tab
        tasks_tab = self._create_tasks_tab()
        tabs.addTab(tasks_tab, "Tasks")
        
        # Logs tab
        logs_tab = self._create_logs_tab()
        tabs.addTab(logs_tab, "Logs")
        
        # History tab (run history + step details)
        history_tab = self._create_history_tab()
        tabs.addTab(history_tab, "Runs")

    def _create_runs_console_page(self) -> QWidget:
        """
        Create the main runs console page with a split view:
        - Left: Runs/History/Jobs/Tasks tabs
        - Right: Console output and logs
        """
        page = QWidget()
        main_layout = QVBoxLayout(page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create the main horizontal splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(6)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #2f3744;
                border: 1px solid #444c66;
            }
            QSplitter::handle:hover {
                background-color: #4f79ff;
            }
        """)

        # Left Pane - Tabs for Jobs/Tasks/Logs/History
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # Create tab widget for left pane
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #2f3744;
                border-radius: 4px;
                padding: 4px;
            }
            QTabBar::tab {
                background-color: #2d3650;
                color: #cfd8e3;
                border: 1px solid #2f3744;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 12px;
                margin-right: 2px;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                background-color: #4f79ff;
                color: white;
                border-color: #4f79ff;
            }
            QTabBar::tab:hover:!selected {
                background-color: #3a4567;
            }
        """)

        # Add tabs to left pane
        jobs_tab = self._create_jobs_tab()
        tasks_tab = self._create_tasks_tab()
        logs_tab = self._create_logs_tab()
        history_tab = self._create_history_tab()
        
        tabs.addTab(jobs_tab, "Jobs")
        tabs.addTab(tasks_tab, "Tasks")
        tabs.addTab(logs_tab, "Logs")
        tabs.addTab(history_tab, "Run History")
        
        left_layout.addWidget(tabs)
        splitter.addWidget(left_widget)

        # Right Pane - Console and Logs
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        # Add console panel
        console_panel = self._create_console_panel()
        right_layout.addWidget(console_panel, 1)  # Console takes most space

        # Add logs panel
        logs_panel = self._create_logs_panel()
        right_layout.addWidget(logs_panel, 1)  # Logs take remaining space

        # Add status strip at the bottom
        status_strip = self._create_status_strip()
        right_layout.addWidget(status_strip)

        splitter.addWidget(right_widget)

        # Set initial splitter sizes (40% left, 60% right)
        splitter.setSizes([self.width() * 0.4, self.width() * 0.6])

        main_layout.addWidget(splitter)
        return page

    def _create_workflow_status_page(self) -> QWidget:
        """
        Create the workflow status page with tabs for workflow graph, Airflow, and system status.
        
        Returns:
            QWidget: The configured workflow status page widget
        """
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Header with title and refresh button
        header = QHBoxLayout()
        title = QLabel("Workflow & Airflow")
        title.setStyleSheet("""
            font-size: 18px; 
            font-weight: 700; 
            color: #e8e8e8;
            padding: 4px 0;
        """)
        header.addWidget(title)
        header.addStretch()
        
        # Auto-refresh toggle
        self.auto_refresh_cb = QCheckBox("Auto-refresh")
        self.auto_refresh_cb.setChecked(True)
        self.auto_refresh_cb.stateChanged.connect(self._toggle_auto_refresh_workflow)
        header.addWidget(self.auto_refresh_cb)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh Now")
        refresh_btn.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        refresh_btn.setStyleSheet("padding: 4px 12px;")
        refresh_btn.clicked.connect(self._refresh_workflow_graph)
        header.addWidget(refresh_btn)
        
        layout.addLayout(header)
        
        # Create tab widget
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #2f3744;
                border-radius: 4px;
                padding: 4px;
                margin-top: 4px;
            }
            QTabBar::tab {
                background-color: #2d3650;
                color: #cfd8e3;
                border: 1px solid #2f3744;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 16px;
                margin-right: 2px;
                font-weight: 500;
                min-width: 80px;
            }
            QTabBar::tab:selected {
                background-color: #4f79ff;
                color: white;
                border-color: #4f79ff;
            }
            QTabBar::tab:hover:!selected {
                background-color: #3a4567;
            }
        """)
        
        # Workflow tab
        workflow_tab = self._create_workflow_tab()
        tabs.addTab(workflow_tab, "Workflow")
        
        # Airflow tab
        airflow_tab = self._create_airflow_tab()
        tabs.addTab(airflow_tab, "Airflow")
        
        # Status tab
        status_tab = self._create_status_tab()
        tabs.addTab(status_tab, "System Status")
        
        layout.addWidget(tabs, 1)  # Take remaining space
        
        return page

    def _create_setup_page(self) -> QWidget:
        """Page 3: setup checklist and environment info."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(15)

        title = QLabel("Setup Checklist")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #e8e8e8;")
        layout.addWidget(title)

        desc = QLabel("The UI validates required prerequisites and can run auto-setup for you.")
        desc.setStyleSheet("color: #a0a7b4; font-size: 14px;")
        layout.addWidget(desc)

        controls = QHBoxLayout()
        run_auto = QPushButton("Run automatic setup")
        run_auto.clicked.connect(self._run_auto_setup)
        controls.addWidget(run_auto)

        refresh_btn = QPushButton("Refresh checks")
        refresh_btn.clicked.connect(self._refresh_setup_status)
        controls.addWidget(refresh_btn)
        controls.addStretch()
        layout.addLayout(controls)

        self.setup_checklist = QListWidget()
        self.setup_checklist.setStyleSheet(
            """
            QListWidget { 
                background: #1c212d; 
                border: 2px solid #2f3744; 
                border-radius: 8px;
                padding: 8px;
            }
            QListWidget::item {
                padding: 10px;
                border-radius: 6px;
                margin-bottom: 4px;
            }
            QListWidget::item:selected {
                background-color: #4f79ff;
            }
            """
        )
        layout.addWidget(self.setup_checklist)

        self.setup_info = QTextBrowser()
        self.setup_info.setOpenExternalLinks(True)
        self.setup_info.setStyleSheet("""
            background: #1c212d; 
            border: 2px solid #2f3744; 
            border-radius: 8px; 
            color: #e8e8e8;
            padding: 10px;
        """)
        self.setup_info.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.setup_info, 1)

        self._render_setup_checklist()
        return page

    def _render_setup_checklist(self) -> None:
        """Populate setup checklist UI from current status."""
        items = self._setup_status_items()
        self.setup_checklist.clear()
        for text, ok in items:
            item = QListWidgetItem(text)
            if ok:
                item.setIcon(self.style().standardIcon(QStyle.SP_DialogApplyButton))
                item.setForeground(QColor("#6ee7a5"))
                item.setBackground(QColor("#253a25"))
            else:
                item.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxWarning))
                item.setForeground(QColor("#f39c12"))
                item.setBackground(QColor("#3a2d1a"))
            item.setData(Qt.UserRole, ok)
            item.setToolTip("OK" if ok else "Missing/Check")
            item.setFont(self._bold_font() if not ok else self.font())
            self.setup_checklist.addItem(item)

        self.setup_info.setHtml(self._setup_instructions_html(items))

    def _refresh_setup_status(self) -> None:
        """Re-run checklist without forcing auto setup."""
        self._render_setup_checklist()

    def _run_auto_setup(self) -> None:
        """Run automatic setup then refresh checklist."""
        self.setup_snapshot = self._auto_initialize_environment()
        self._render_setup_checklist()

    def _auto_initialize_environment(self) -> Dict[str, Any]:
        """
        Prepare baseline environment (directories, local DB, secrets) for first run.
        """
        snapshot: Dict[str, Any] = {"created_paths": [], "errors": []}
        required_dirs = [
            Path("sessions"),
            Path("sessions/cookies"),
            Path("sessions/logs"),
            Path("output"),
            Path("input"),
            Path("logs"),
        ]

        for path in required_dirs:
            try:
                path.mkdir(parents=True, exist_ok=True)
                snapshot["created_paths"].append(str(path.resolve()))
            except Exception as exc:  # pragma: no cover - defensive
                snapshot["errors"].append(f"Directory {path}: {exc}")

        if not os.getenv("DB_URL") and not os.getenv("RUN_DB_PATH"):
            default_db = Path("logs/run_tracking.sqlite")
            try:
                default_db.parent.mkdir(parents=True, exist_ok=True)
                os.environ["RUN_DB_PATH"] = str(default_db.resolve())
                snapshot["run_db_path"] = str(default_db.resolve())
            except Exception as exc:  # pragma: no cover - defensive
                snapshot["errors"].append(f"Run DB path: {exc}")

        try:
            snapshot["storage"] = run_db.initialize_run_storage()
        except Exception as exc:  # pragma: no cover - defensive
            snapshot["storage"] = {"backend": "error", "location": str(exc)}
            snapshot["errors"].append(f"Run storage: {exc}")

        key_env = os.getenv("SCRAPER_SECRET_KEY")
        key_file = Path(os.getenv("SCRAPER_SECRET_KEY_FILE", _DEFAULT_KEY_PATH))
        if not key_env and not key_file.exists():
            try:
                key_file.parent.mkdir(parents=True, exist_ok=True)
                key = Fernet.generate_key().decode("ascii")
                key_file.write_text(key, encoding="ascii")
                snapshot["generated_key"] = str(key_file)
            except Exception as exc:  # pragma: no cover - defensive
                snapshot["errors"].append(f"Secret key: {exc}")

        snapshot["airflow_installed"] = self.airflow_service.is_airflow_installed()
        snapshot["required_dirs"] = [str(p) for p in required_dirs]
        return snapshot
    
    def _create_jobs_tab(self) -> QWidget:
        """Create the jobs list tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("Job Management")
        title.setStyleSheet("font-size: 18px; font-weight: 600; color: #e8e8e8; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Toolbar for jobs
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        
        # Source selector
        toolbar.addWidget(QLabel("Source:"))
        self.source_combo = QComboBox()
        self.source_combo.addItems(["alfabeta", "argentina", "chile", "lafa", "quebec", "template"])
        self.source_combo.setMinimumWidth(120)
        toolbar.addWidget(self.source_combo)
        
        # Run type
        toolbar.addWidget(QLabel("Run Type:"))
        self.run_type_combo = QComboBox()
        self.run_type_combo.addItems(["FULL_REFRESH", "DELTA", "SINGLE_PRODUCT"])
        self.run_type_combo.setMinimumWidth(150)
        toolbar.addWidget(self.run_type_combo)
        
        # Environment
        toolbar.addWidget(QLabel("Environment:"))
        self.env_combo = QComboBox()
        self.env_combo.addItems(["dev", "staging", "prod"])
        self.env_combo.setMinimumWidth(100)
        toolbar.addWidget(self.env_combo)
        
        # Start button
        self.start_btn = QPushButton("Start Job")
        self.start_btn.clicked.connect(self._start_job)
        self.start_btn.setStyleSheet("background-color: #51cf66; font-weight: 600;")
        toolbar.addWidget(self.start_btn)
        
        # Stop button
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self._stop_job)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("background-color: #ff6b6b; font-weight: 600;")
        toolbar.addWidget(self.stop_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Jobs table
        self.jobs_table = QTableWidget()
        self.jobs_table.setColumnCount(6)
        self.jobs_table.setHorizontalHeaderLabels([
            "Run ID", "Source", "Status", "Started", "Duration", "Items"
        ])
        self.jobs_table.horizontalHeader().setStretchLastSection(True)
        self.jobs_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.jobs_table.itemSelectionChanged.connect(self._on_job_selected)
        # Improve selection highlighting
        self.jobs_table.setStyleSheet("""
            QTableWidget::item:selected {
                background-color: #4f79ff;
                color: white;
            }
            QTableWidget::item:hover {
                background-color: #2d3650;
            }
            QHeaderView::section {
                background-color: #2d3650;
                color: #cfd8e3;
                padding: 6px;
                border: 1px solid #444c66;
            }
        """)
        layout.addWidget(self.jobs_table)
        
        return widget
    
    def _create_tasks_tab(self) -> QWidget:
        """Create the tasks list tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("Task Execution")
        title.setStyleSheet("font-size: 18px; font-weight: 600; color: #e8e8e8; margin-bottom: 10px;")
        layout.addWidget(title)
        
        self.tasks_tree = QTreeWidget()
        self.tasks_tree.setHeaderLabels(["Task", "Status", "Duration", "Output"])
        self.tasks_tree.setColumnWidth(0, 200)
        self.tasks_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #0f1115;
                color: #eaeaea;
                border: 1px solid #2e3238;
                border-radius: 4px;
                padding: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #2a3b55;
                color: #ffffff;
            }
            QTreeWidget::item:hover {
                background-color: #1b2432;
            }
            QHeaderView::section {
                background-color: #181c24;
                color: #cfd3da;
                padding: 6px;
                border: 1px solid #2e3238;
                font-weight: 600;
            }
        """)
        layout.addWidget(self.tasks_tree)
        
        return widget
    
    def _create_logs_tab(self) -> QWidget:
        """Create the logs tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("Application Logs")
        title.setStyleSheet("font-size: 18px; font-weight: 600; color: #e8e8e8; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Filter toolbar
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        
        filter_layout.addWidget(QLabel("Filter:"))
        self.log_filter = QLineEdit()
        self.log_filter.setPlaceholderText("Search logs...")
        self.log_filter.textChanged.connect(self._filter_logs)
        self.log_filter.setMinimumWidth(200)
        filter_layout.addWidget(self.log_filter)
        
        # Level filter
        filter_layout.addWidget(QLabel("Level:"))
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.currentTextChanged.connect(self._filter_logs)
        self.log_level_combo.setMinimumWidth(120)
        filter_layout.addWidget(self.log_level_combo)
        
        export_btn = QPushButton("Export Logs")
        export_btn.clicked.connect(self._export_logs)
        filter_layout.addWidget(export_btn)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Logs text area
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setFontFamily("Consolas")
        self.logs_text.setFontPointSize(9)
        self.logs_text.setStyleSheet("""
            QTextEdit {
                background-color: #1c212d;
                color: #e8e8e8;
                border: 2px solid #2f3744;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.logs_text)
        
        return widget
    
    def _create_history_tab(self) -> QWidget:
        """Create the run history tab with run and step detail views."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("Run History")
        title.setStyleSheet("font-size: 18px; font-weight: 600; color: #e8e8e8; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Toolbar with filter + refresh
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        
        toolbar.addWidget(QLabel("Search:"))
        self.history_search = QLineEdit()
        self.history_search.setPlaceholderText("Filter by run id / source / status")
        self.history_search.textChanged.connect(self._filter_history)
        self.history_search.setMinimumWidth(160)
        toolbar.addWidget(self.history_search)

        toolbar.addWidget(QLabel("Source:"))
        self.history_source_filter = QComboBox()
        self.history_source_filter.addItem("All")
        self.history_source_filter.currentIndexChanged.connect(self._filter_history)
        self.history_source_filter.setMinimumWidth(100)
        toolbar.addWidget(self.history_source_filter)

        toolbar.addWidget(QLabel("Status:"))
        self.history_status_filter = QComboBox()
        self.history_status_filter.addItems(["All", "success", "failed", "partial", "running"])
        self.history_status_filter.currentIndexChanged.connect(self._filter_history)
        self.history_status_filter.setMinimumWidth(100)
        toolbar.addWidget(self.history_status_filter)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_run_history)
        toolbar.addWidget(refresh_btn)

        self.open_output_btn = QPushButton("Open Output")
        self.open_output_btn.clicked.connect(self._open_selected_output)
        toolbar.addWidget(self.open_output_btn)

        self.open_folder_btn = QPushButton("Open Folder")
        self.open_folder_btn.clicked.connect(self._open_selected_folder)
        toolbar.addWidget(self.open_folder_btn)

        # Pagination
        self.history_prev_btn = QPushButton("Prev")
        self.history_prev_btn.clicked.connect(self._history_prev_page)
        toolbar.addWidget(self.history_prev_btn)
        self.history_next_btn = QPushButton("Next")
        self.history_next_btn.clicked.connect(self._history_next_page)
        toolbar.addWidget(self.history_next_btn)
        self.history_page_label = QLabel("Page 1")
        toolbar.addWidget(self.history_page_label)
        toolbar.addWidget(QLabel("Page size:"))
        self.history_page_size_combo = QComboBox()
        self.history_page_size_combo.addItems(["10", "15", "25", "50"])
        self.history_page_size_combo.setCurrentText(str(self.history_page_size))
        self.history_page_size_combo.currentTextChanged.connect(self._on_history_page_size)
        toolbar.addWidget(self.history_page_size_combo)

        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Runs table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels(
            ["Run ID", "Source", "Status", "Start", "Duration (s)", "Items", "Error"]
        )
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setSelectionMode(QTableWidget.SingleSelection)
        self.history_table.itemSelectionChanged.connect(self._load_selected_run_detail)
        # Improve selection highlighting
        self.history_table.setStyleSheet("""
            QTableWidget::item:selected {
                background-color: #4f79ff;
                color: white;
            }
            QTableWidget::item:hover {
                background-color: #2d3650;
            }
            QHeaderView::section {
                background-color: #2d3650;
                color: #cfd8e3;
                padding: 6px;
                border: 1px solid #444c66;
                font-weight: 600;
            }
        """)
        layout.addWidget(self.history_table)
        
        # Detail + steps section
        detail_splitter = QSplitter(Qt.Vertical)
        detail_splitter.setHandleWidth(8)
        detail_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #2f3744;
                border: 1px solid #444c66;
            }
        """)
        
        # Run detail summary
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_title = QLabel("Run Detail")
        detail_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #cfd8e3; padding: 5px;")
        detail_layout.addWidget(detail_title)
        self.history_detail = QTextEdit()
        self.history_detail.setReadOnly(True)
        self.history_detail.setMinimumHeight(120)
        self.history_detail.setStyleSheet("""
            QTextEdit {
                background-color: #1c212d;
                color: #e8e8e8;
                border: 2px solid #2f3744;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        detail_layout.addWidget(self.history_detail)
        detail_splitter.addWidget(detail_widget)
        
        # Steps table
        steps_widget = QWidget()
        steps_layout = QVBoxLayout(steps_widget)
        steps_layout.setContentsMargins(0, 0, 0, 0)
        steps_title = QLabel("Steps")
        steps_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #cfd8e3; padding: 5px;")
        steps_layout.addWidget(steps_title)
        self.history_steps_table = QTableWidget()
        self.history_steps_table.setColumnCount(4)
        self.history_steps_table.setHorizontalHeaderLabels(["Step", "Status", "Start", "Duration (s)"])
        self.history_steps_table.horizontalHeader().setStretchLastSection(True)
        self.history_steps_table.setStyleSheet("""
            QTableWidget::item:selected {
                background-color: #4f79ff;
                color: white;
            }
            QTableWidget::item:hover {
                background-color: #2d3650;
            }
            QHeaderView::section {
                background-color: #2d3650;
                color: #cfd8e3;
                padding: 6px;
                border: 1px solid #444c66;
                font-weight: 600;
            }
        """)
        steps_layout.addWidget(self.history_steps_table)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("Workflow Visualization")
        title.setStyleSheet("font-size: 18px; font-weight: 600; color: #e8e8e8; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Controls toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        
        refresh_btn = QPushButton("Refresh Graph")
        refresh_btn.clicked.connect(self._refresh_workflow_graph)
        refresh_btn.setStyleSheet("font-weight: 600;")
        toolbar.addWidget(refresh_btn)
        
        auto_refresh_cb = QCheckBox("Auto-refresh every 30s")
        auto_refresh_cb.stateChanged.connect(self._toggle_auto_refresh_workflow)
        toolbar.addWidget(auto_refresh_cb)
        
        # Zoom controls
        zoom_in_btn = QPushButton("Zoom In")
        zoom_in_btn.clicked.connect(self._zoom_in_workflow)
        toolbar.addWidget(zoom_in_btn)
        
        zoom_out_btn = QPushButton("Zoom Out")
        zoom_out_btn.clicked.connect(self._zoom_out_workflow)
        toolbar.addWidget(zoom_out_btn)
        
        reset_view_btn = QPushButton("Reset View")
        reset_view_btn.clicked.connect(self._reset_workflow_view)
        toolbar.addWidget(reset_view_btn)
        
        toolbar.addStretch()
        
        export_btn = QPushButton("Export Graph")
        export_btn.clicked.connect(self._export_workflow_graph)
        toolbar.addWidget(export_btn)
        
        layout.addLayout(toolbar)
        
        # Workflow graph widget
        self.workflow_graph = WorkflowGraphWidget()
        layout.addWidget(self.workflow_graph)
        
        # Status info
        self.workflow_status = QLabel("Graph loaded successfully")
        self.workflow_status.setStyleSheet("color: #51cf66; font-style: italic; padding: 5px;")
        layout.addWidget(self.workflow_status)
        
        return widget
    
    def _create_airflow_tab(self) -> QWidget:
        """Create the Airflow DAG view tab with service management."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("Airflow Services & DAG Management")
        title.setStyleSheet("font-size: 18px; font-weight: 600; color: #e8e8e8; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Service management section
        service_group = QGroupBox("Service Management")
        service_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #2f3744;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                color: #cfd8e3;
            }
        """)
        service_layout = QVBoxLayout(service_group)
        service_layout.setContentsMargins(10, 10, 10, 10)
        
        # Service controls toolbar
        service_toolbar = QHBoxLayout()
        
        # Start/Stop Airflow button
        self.airflow_start_btn = QPushButton("Start Airflow Services")
        self.airflow_start_btn.clicked.connect(self._start_airflow_services)
        service_toolbar.addWidget(self.airflow_start_btn)
        
        self.airflow_stop_btn = QPushButton("Stop Airflow Services")
        self.airflow_stop_btn.clicked.connect(self._stop_airflow_services)
        self.airflow_stop_btn.setEnabled(False)
        service_toolbar.addWidget(self.airflow_stop_btn)
        
        # Status label
        self.airflow_service_status = QLabel("Status: Not running")
        self.airflow_service_status.setStyleSheet("color: #ff6b6b; font-weight: bold; padding: 8px; font-size: 14px;")
        service_toolbar.addWidget(self.airflow_service_status)
        
        service_toolbar.addStretch()
        service_layout.addLayout(service_toolbar)
        
        # Info label
        info_label = QLabel(
            "Airflow services can be started automatically from this UI.\n"
            "The scheduler and API server will run in the background."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("""
            background-color: #252a3a; 
            padding: 12px; 
            border-radius: 6px;
            border: 1px solid #2f3744;
        """)
        service_layout.addWidget(info_label)
        
        layout.addWidget(service_group)
        
        # Connection section
        connection_group = QGroupBox("Connection & Control")
        connection_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #2f3744;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                color: #cfd8e3;
            }
        """)
        connection_layout = QVBoxLayout(connection_group)
        connection_layout.setContentsMargins(10, 10, 10, 10)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        # Airflow URL input
        toolbar.addWidget(QLabel("Airflow URL:"))
        self.airflow_url = QLineEdit()
        self.airflow_url.setText("http://localhost:8080")
        self.airflow_url.setPlaceholderText("http://localhost:8080")
        self.airflow_url.setMinimumWidth(200)
        toolbar.addWidget(self.airflow_url)
        
        # Check connection button
        check_btn = QPushButton("Check Connection")
        check_btn.clicked.connect(self._check_airflow_connection)
        toolbar.addWidget(check_btn)
        
        # Connect button
        connect_btn = QPushButton("Connect")
        connect_btn.clicked.connect(self._connect_airflow)
        toolbar.addWidget(connect_btn)
        
        # Control buttons
        pause_btn = QPushButton("Pause DAG")
        pause_btn.clicked.connect(self._pause_dag)
        toolbar.addWidget(pause_btn)
        
        resume_btn = QPushButton("Resume DAG")
        resume_btn.clicked.connect(self._resume_dag)
        toolbar.addWidget(resume_btn)
        
        toolbar.addStretch()
        connection_layout.addLayout(toolbar)
        
        # Connection status label
        self.airflow_status_label = QLabel("Connection: Not connected")
        self.airflow_status_label.setStyleSheet("color: #ff6b6b; font-weight: bold; padding: 8px; font-size: 14px;")
        connection_layout.addWidget(self.airflow_status_label)
        
        layout.addWidget(connection_group)
        
        # Web view for Airflow UI
        webview_group = QGroupBox("Airflow Web Interface")
        webview_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #2f3744;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                color: #cfd8e3;
            }
        """)
        webview_layout = QVBoxLayout(webview_group)
        webview_layout.setContentsMargins(10, 10, 10, 10)
        
        self.airflow_webview = QWebEngineView()
        # Don't auto-load - wait for user to connect
        self.airflow_webview.setHtml("""
            <html>
            <body style="background-color: #1e1e1e; color: #cccccc; font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: #4f79ff;">Airflow Desktop Integration</h2>
                <p>Click "Start Airflow Services" to launch the scheduler and API server.</p>
                <p>Then click "Connect" to load the Airflow UI.</p>
                <div style="background-color: #252a3a; padding: 15px; border-radius: 8px; margin: 15px 0;">
                    <h3 style="color: #51cf66;">Features</h3>
                    <ul>
                        <li>Start and stop Airflow services from the UI</li>
                        <li>Embedded Airflow UI without opening a browser</li>
                        <li>Basic service management built-in</li>
                        <li>Status feedback for scheduler and API server</li>
                    </ul>
                </div>
                <p style="font-style: italic; color: #a0a7b4;">Note: On Windows, Airflow typically requires Docker or WSL2 for full operation.</p>
            </body>
            </html>
        """)
        webview_layout.addWidget(self.airflow_webview)
        layout.addWidget(webview_group)
        
        return widget
    
    def _create_status_tab(self) -> QWidget:
        """Create the status indicators tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Title
        title = QLabel("System Status")
        title.setStyleSheet("font-size: 18px; font-weight: 600; color: #e8e8e8; margin-bottom: 15px;")
        layout.addWidget(title)
        
        # Status indicators will be added here
        self.status_label = QLabel("System Status: Ready")
        self.status_label.setStyleSheet("""
            font-size: 16px; 
            font-weight: 600; 
            color: #51cf66; 
            padding: 15px; 
            background-color: #252a3a; 
            border: 2px solid #2f3744; 
            border-radius: 8px;
        """)
        layout.addWidget(self.status_label)
        
        # Add more status information
        status_grid = QGridLayout()
        status_grid.setSpacing(15)
        
        # System info cards
        cpu_card = self._create_status_card("CPU Usage", "0%", "#4f79ff")
        mem_card = self._create_status_card("Memory", "0 MB", "#51cf66")
        disk_card = self._create_status_card("Disk Space", "0 GB", "#ffd43b")
        network_card = self._create_status_card("Network", "Connected", "#51cf66")
        
        status_grid.addWidget(cpu_card, 0, 0)
        status_grid.addWidget(mem_card, 0, 1)
        status_grid.addWidget(disk_card, 1, 0)
        status_grid.addWidget(network_card, 1, 1)
        
        layout.addLayout(status_grid)
        layout.addStretch()
        return widget
    
    def _create_status_card(self, title: str, value: str, color: str) -> QWidget:
        """Create a status card widget."""
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(f"""
            background-color: #252a3a;
            border: 2px solid #2f3744;
            border-radius: 10px;
            padding: 15px;
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #cfd8e3; font-size: 14px; font-weight: 600;")
        
        value_label = QLabel(value)
        value_label.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: 700;")
        
        layout.addWidget(title_label, 0, Qt.AlignCenter)
        layout.addWidget(value_label, 0, Qt.AlignCenter)
        
        return card
    
    def _create_console_panel(self) -> QWidget:
        """Console output panel (placed on the right side of Runs page)."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        
        console_label = QLabel("Console Output:")
        console_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #cfd8e3; padding: 4px;")
        layout.addWidget(console_label)
        
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setFontFamily("Consolas")
        self.console_output.setFontPointSize(10)
        self.console_output.setStyleSheet("""
            background-color: #000000;
            color: #ffd447;
            border: 1px solid #333333;
            border-radius: 2px;
            padding: 8px;
        """)
        layout.addWidget(self.console_output)
        
        return widget

    def _create_logs_panel(self) -> QWidget:
        """Compact logs panel with filters."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        header = QHBoxLayout()
        lbl = QLabel("Logs")
        lbl.setStyleSheet("font-weight: 600; color: #cfd3da;")
        header.addWidget(lbl)
        header.addStretch()

        self.log_filter_job = QLineEdit()
        self.log_filter_job.setPlaceholderText("Job ID")
        self.log_filter_job.textChanged.connect(self._render_logs)
        header.addWidget(self.log_filter_job)

        self.log_filter_module = QLineEdit()
        self.log_filter_module.setPlaceholderText("Module")
        self.log_filter_module.textChanged.connect(self._render_logs)
        header.addWidget(self.log_filter_module)

        self.log_filter_level = QComboBox()
        self.log_filter_level.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_filter_level.currentTextChanged.connect(self._render_logs)
        header.addWidget(self.log_filter_level)

        layout.addLayout(header)

        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setFontFamily("Consolas")
        self.logs_text.setFontPointSize(9)
        self.logs_text.setStyleSheet("""
            background-color: #0f1115;
            color: #eaeaea;
            border: 1px solid #2e3238;
            border-radius: 4px;
            padding: 6px;
        """)
        layout.addWidget(self.logs_text)
        return widget

    def _create_status_strip(self) -> QWidget:
        """Compact status strip."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(12)
        self.summary_status_card, self.summary_status_val = self._status_chip("Status")
        self.summary_items_card, self.summary_items_val = self._status_chip("Items")
        self.summary_error_card, self.summary_error_val = self._status_chip("Last Error")
        self.summary_error_val.setWordWrap(True)
        layout.addWidget(self.summary_status_card)
        layout.addWidget(self.summary_items_card)
        layout.addWidget(self.summary_error_card, 1)
        return widget

    def _create_timeline_panel(self) -> QWidget:
        """Simple timeline list of recent events."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        lbl = QLabel("Recent events")
        lbl.setStyleSheet("font-weight: 600; color: #cfd3da;")
        layout.addWidget(lbl)
        self.timeline_list = QListWidget()
        self.timeline_list.setStyleSheet("""
            QListWidget {
                background-color: #0f1115;
                color: #eaeaea;
                border: 1px solid #2e3238;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        layout.addWidget(self.timeline_list, 1)
        return widget

    def _on_pipeline_finished(self, result: Dict[str, Any]) -> None:
        """Handle pipeline completion."""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        status = result.get("status", "unknown")
        self._add_event("JOB_FINISHED", status=status, result=result)
        self._refresh_job_list()
        self._refresh_run_history()
        
        if status == "failed":
            err = result.get("error") or ""
            QMessageBox.warning(self, "Job Failed", f"Pipeline failed: {err or 'Unknown error'}")
        else:
            QMessageBox.information(self, "Job Completed", "Pipeline finished successfully.")
    
    def _setup_menu_bar(self) -> None:
        """Setup the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        export_action = QAction("Export Logs...", self)
        export_action.triggered.connect(self._export_logs)
        file_menu.addAction(export_action)
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        dark_action = QAction("Dark Theme", self)
        dark_action.triggered.connect(lambda: self._apply_theme("dark"))
        view_menu.addAction(dark_action)
        
        light_action = QAction("Light Theme", self)
        light_action.triggered.connect(lambda: self._apply_theme("light"))
        view_menu.addAction(light_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_toolbar(self) -> None:
        """Setup the toolbar."""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        # Refresh button
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self._refresh_job_list)
        toolbar.addAction(refresh_action)
    
    def _setup_status_bar(self) -> None:
        """Setup the status bar."""
        self.statusBar().showMessage("Ready")
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress_bar)
    
    def _setup_logging(self) -> None:
        """Setup UI logging handler."""
        import logging
        # Create handler with proper parent
        ui_handler = UILoggingHandler(self)
        ui_handler.message_logged.connect(self._on_log_message)
        # Add to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(ui_handler)
        # Store reference to prevent garbage collection
        self._ui_log_handler = ui_handler
    
    def _apply_theme(self, theme: str) -> None:
        """Apply a theme (dark or light)."""
        self.theme_manager.apply_theme(self, theme)
    
    def _start_job(self) -> None:
        """Start a new pipeline job."""
        source = self.source_combo.currentText()
        run_type = self.run_type_combo.currentText()
        environment = self.env_combo.currentText()
        job_id = f"{source}-{datetime.utcnow().strftime('%H%M%S')}"

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate

        self.job_manager.start_job(job_id, source=source, run_type=run_type, environment=environment)
        self._append_console(f"[INFO] Started job {job_id}")
        self._add_event("JOB_STARTED", source=source, run_type=run_type, environment=environment)
        self._refresh_job_list()
        self._push_timeline(f"Started {job_id} ({source})")
    
    def _stop_job(self) -> None:
        """Stop the current pipeline job."""
        row = self.jobs_table.currentRow()
        if row >= 0:
            job_id = self.jobs_table.item(row, 0).text()
            self.job_manager.stop_job(job_id)
            self._append_console(f"[INFO] Stopped job {job_id}")
            self._add_event("JOB_CANCELLED", job_id=job_id)
            self._refresh_job_list()
            self._push_timeline(f"Stopped {job_id}")
    
    def _on_pipeline_log(self, level: str, message: str) -> None:
        """Handle log message from pipeline."""
        self._append_console(f"[{level}] {message}")
        self._append_log_area(f"[{level}] {message}")
    
    def _on_pipeline_finished(self, result: Dict[str, Any]) -> None:
        """Handle pipeline completion."""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        status = result.get("status", "unknown")
        self._add_event("JOB_FINISHED", status=status, result=result)
        self._refresh_job_list()
        
        if status == "failed":
            QMessageBox.warning(self, "Job Failed", f"Pipeline failed: {result.get('error', 'Unknown error')}")
        else:
            QMessageBox.information(self, "Job Complete", "Pipeline completed successfully!")
    
    def _on_job_selected(self) -> None:
        """Handle job selection."""
        selected = self.jobs_table.selectedItems()
        if selected:
            run_id = self.jobs_table.item(self.jobs_table.currentRow(), 0).text()
            self._populate_tasks_for_run(run_id)
            self._populate_run_detail_from_jobs(run_id)
    
    def _refresh_job_list(self) -> None:
        """Refresh the job list from the database."""
        try:
            jobs = self.job_manager.list_jobs()
            rows = list(jobs.values())
            self.jobs_table.setRowCount(len(rows))
            for i, info in enumerate(rows):
                status = info.status
                def _badge_color(s: str) -> str:
                    return {
                        "running": "#1f7a1f",
                        "completed": "#4f79ff",
                        "failed": "#c0392b",
                        "stopped": "#c0392b",
                        "pending": "#d4ac0d",
                    }.get(s, "#7f8c8d")
                self.jobs_table.setItem(i, 0, QTableWidgetItem(info.job_id))
                self.jobs_table.setItem(i, 1, QTableWidgetItem(info.source))
                status_item = QTableWidgetItem(status)
                status_item.setBackground(QColor(_badge_color(status)))
                status_item.setForeground(QColor("#ffffff"))
                self.jobs_table.setItem(i, 2, status_item)
                started = datetime.fromtimestamp(info.started_at) if info.started_at else None
                ended = datetime.fromtimestamp(info.ended_at) if info.ended_at else None
                self.jobs_table.setItem(i, 3, QTableWidgetItem(self._format_dt(started)))
                duration = ""
                if started and ended:
                    duration = str(int((ended - started).total_seconds()))
                self.jobs_table.setItem(i, 4, QTableWidgetItem(duration))
                items_val = info.result.get("item_count") if info.result else ""
                self.jobs_table.setItem(i, 5, QTableWidgetItem("" if items_val is None else str(items_val)))
            if rows:
                self.jobs_table.selectRow(0)
        except Exception as exc:
            log.error("Failed to refresh jobs: %s", exc)
            self.jobs_table.setRowCount(0)
    
    def _filter_logs(self) -> None:
        """Filter logs based on search text and level."""
        # TODO: Implement log filtering
        pass
    
    def _filter_history(self) -> None:
        """Filter event history."""
        search_text = self.history_search.text().lower()
        # TODO: Implement history filtering
        pass
    
    def _export_history_csv(self) -> None:
        """Export event history to CSV."""
        filename, _ = QFileDialog.getSaveFileName(self, "Export History", "", "CSV Files (*.csv)")
        if filename:
            # TODO: Implement CSV export
            pass
    
    def _export_history_json(self) -> None:
        """Export event history to JSON."""
        filename, _ = QFileDialog.getSaveFileName(self, "Export History", "", "JSON Files (*.json)")
        if filename:
            with open(filename, 'w') as f:
                json.dump(self.event_history, f, indent=2, default=str)
            QMessageBox.information(self, "Export Complete", f"History exported to {filename}")
    
    def _start_airflow_services(self) -> None:
        """Start Airflow services (scheduler and API server)."""
        # Check if Airflow is installed
        if not self.airflow_service.is_airflow_installed():
            # Try one more time with import check
            try:
                import airflow
                # If import succeeds, update the service to know Airflow is available
                log.info("Airflow found via import check")
            except ImportError:
                QMessageBox.warning(
                    self,
                    "Airflow Not Found",
                    "Airflow installation not detected.\n\n"
                    "Even though Airflow may be installed, the application cannot find it.\n\n"
                    "Troubleshooting:\n"
                    "1. Ensure Airflow is installed: pip install apache-airflow\n"
                    "2. Restart the application after installation\n"
                    "3. Check if 'airflow' command works in terminal\n"
                    "4. Verify Python environment matches the one used by this app"
                )
                return
        
        self.airflow_start_btn.setEnabled(False)
        self.airflow_service_status.setText("Status: Starting...")
        self.airflow_service_status.setStyleSheet("color: #ffd43b; font-weight: bold; padding: 5px;")
        
        # Start services in a QThread (proper Qt threading)
        self.airflow_start_thread = AirflowServiceStartThread(self.airflow_service)
        self.airflow_start_thread.started.connect(self._on_airflow_services_started)
        self.airflow_start_thread.status_update.connect(self._on_airflow_status_update)
        self.airflow_start_thread.start()
    
    def _on_airflow_services_started(self, success: bool, message: str) -> None:
        """Handle Airflow services start completion."""
        if success:
            self.airflow_service_status.setText("Status: ✅ Running")
            self.airflow_service_status.setStyleSheet("color: #51cf66; font-weight: bold; padding: 5px;")
            self.airflow_start_btn.setEnabled(False)
            self.airflow_stop_btn.setEnabled(True)
            self.airflow_status_label.setText("Connection: Ready to connect")
            self.airflow_status_label.setStyleSheet("color: #51cf66; font-weight: bold;")
        else:
            self.airflow_service_status.setText(f"Status: ❌ {message}")
            self.airflow_service_status.setStyleSheet("color: #ff6b6b; font-weight: bold; padding: 5px;")
            self.airflow_start_btn.setEnabled(True)
            # Provide helpful error message
            error_details = f"Failed to start Airflow services.\n\n{message}\n\n"
            
            if "auth" in message.lower() or "auth_manager" in message.lower():
                error_details += (
                    "⚠️ Auth Manager Issue Detected\n\n"
                    "Airflow 3.x requires an auth manager to be configured.\n\n"
                    "To fix:\n"
                    "1. Run: python tools/setup_airflow_auth.py\n"
                    "2. Or manually edit ~/airflow/airflow.cfg\n"
                    "3. Add to [core] section:\n"
                    "   auth_manager = airflow.api_fastapi.auth.managers.simple.simple_auth_manager.SimpleAuthManager\n\n"
                    "Then restart the services.\n\n"
                )
            
            error_details += (
                "Other common issues:\n"
                "- Port 8080 already in use\n"
                "- Database initialization failed\n"
                "- Windows compatibility issues (consider WSL2)\n\n"
                "Check console output for detailed error messages."
            )
            
            QMessageBox.warning(self, "Failed to Start Airflow", error_details)
        self.airflow_start_thread = None
    
    def _on_airflow_status_update(self, status: str) -> None:
        """Handle status updates from service start thread."""
        self.airflow_service_status.setText(f"Status: {status}")
    
    def _stop_airflow_services(self) -> None:
        """Stop Airflow services."""
        reply = QMessageBox.question(
            self,
            "Stop Airflow Services",
            "Are you sure you want to stop Airflow services?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.airflow_service.stop_all()
            self.airflow_service_status.setText("Status: Stopped")
            self.airflow_service_status.setStyleSheet("color: #ff6b6b; font-weight: bold; padding: 5px;")
            self.airflow_start_btn.setEnabled(True)
            self.airflow_stop_btn.setEnabled(False)
            self.airflow_status_label.setText("Connection: Services stopped")
            self.airflow_status_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
            # Clear webview
            self.airflow_webview.setHtml("""
                <html>
                <body style="background-color: #1e1e1e; color: #cccccc; font-family: Arial; padding: 20px;">
                    <h2>Airflow Services Stopped</h2>
                    <p>Click "Start Airflow Services" to restart.</p>
                </body>
                </html>
            """)
    
    def _check_airflow_connection(self) -> None:
        """Check if Airflow is accessible."""
        import urllib.request
        import urllib.error
        
        url = self.airflow_url.text()
        try:
            # Try to connect to Airflow health endpoint
            health_url = url.rstrip('/') + '/health'
            req = urllib.request.Request(health_url)
            req.add_header('User-Agent', 'Scraper-Platform-UI')
            
            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status == 200:
                    self.airflow_status_label.setText("Connection: ✅ Connected")
                    self.airflow_status_label.setStyleSheet("color: #51cf66; font-weight: bold;")
                    QMessageBox.information(self, "Connection Success", "Airflow is running and accessible!")
                else:
                    self.airflow_status_label.setText("Connection: ⚠️ Responding but may have issues")
                    self.airflow_status_label.setStyleSheet("color: #ffd43b; font-weight: bold;")
        except urllib.error.URLError as e:
            self.airflow_status_label.setText("Connection: ❌ Connection refused - Airflow not running")
            self.airflow_status_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
            QMessageBox.warning(
                self,
                "Connection Failed",
                f"Cannot connect to Airflow at {url}\n\n"
                f"Error: {str(e)}\n\n"
                "Click 'Start Airflow Services' to start Airflow automatically,\n"
                "or start it manually:\n"
                "1. Terminal: airflow webserver --port 8080\n"
                "2. Terminal: airflow scheduler"
            )
        except Exception as e:
            self.airflow_status_label.setText(f"Connection: ❌ Error: {str(e)}")
            self.airflow_status_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
            QMessageBox.warning(self, "Connection Error", f"Error checking connection: {str(e)}")
    
    def _connect_airflow(self) -> None:
        """Connect to Airflow webserver."""
        url = self.airflow_url.text()
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please enter an Airflow URL")
            return
        
        # Check if services are running first
        if not self.airflow_service.is_running():
            reply = QMessageBox.question(
                self,
                "Airflow Services Not Running",
                "Airflow services are not running.\n\n"
                "You need to start the services before connecting.\n\n"
                "Steps:\n"
                "1. Click 'Start Airflow Services' button above\n"
                "2. Wait for status to show '✅ Running'\n"
                "3. Then click 'Connect' again\n\n"
                "Would you like to start services now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self._start_airflow_services()
                QMessageBox.information(
                    self,
                    "Services Starting",
                    "Airflow services are starting in the background.\n\n"
                    "Please wait for the status to show '✅ Running'\n"
                    "(usually takes 10-15 seconds),\n"
                    "then click 'Connect' again."
                )
                return
            else:
                return
        
        # Update status
        self.airflow_status_label.setText("Connection: Connecting...")
        self.airflow_status_label.setStyleSheet("color: #ffd43b; font-weight: bold;")
        
        # Set URL - this will show connection error in webview if Airflow isn't running
        self.airflow_webview.setUrl(QUrl(url))
        
        # Update status after a delay (webview doesn't provide easy error detection)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(2000, self._verify_airflow_connection)
    
    def _verify_airflow_connection(self) -> None:
        """Verify that Airflow connection succeeded."""
        # This is called after attempting to connect
        # If services are running, assume connection is good
        if self.airflow_service.is_running():
            self.airflow_status_label.setText("Connection: Connected")
            self.airflow_status_label.setStyleSheet("color: #51cf66; font-weight: bold;")
    
    def _pause_dag(self) -> None:
        """Pause the selected DAG."""
        # TODO: Implement Airflow API call
        QMessageBox.information(self, "Info", "Pause DAG functionality - to be implemented")
    
    def _resume_dag(self) -> None:
        """Resume the selected DAG."""
        # TODO: Implement Airflow API call
        QMessageBox.information(self, "Info", "Resume DAG functionality - to be implemented")
    
    def _format_dt(self, ts: Any) -> str:
        if isinstance(ts, datetime):
            return ts.isoformat(sep=" ", timespec="seconds")
        return str(ts) if ts is not None else ""
    
    def _refresh_run_history(self) -> None:
        """Fetch run history from the tracking store."""
        try:
            runs = run_db.fetch_run_summaries()
            self.run_history = runs
            self._last_history_refresh = datetime.utcnow()
            # Update source filter options
            sources = sorted({r.source for r in runs})
            current = self.history_source_filter.currentText()
            self.history_source_filter.blockSignals(True)
            self.history_source_filter.clear()
            self.history_source_filter.addItem("All")
            for s in sources:
                self.history_source_filter.addItem(s)
            if current in sources or current == "All":
                idx = self.history_source_filter.findText(current)
                if idx >= 0:
                    self.history_source_filter.setCurrentIndex(idx)
            self.history_source_filter.blockSignals(False)
        except Exception as exc:
            log.error("Failed to load run history: %s", exc)
            self.run_history = []
        self._update_history_table()
    
    def _refresh_workflow_graph(self) -> None:
        """Refresh the workflow graph visualization."""
        try:
            self.workflow_graph.refresh()
            self.workflow_status.setText("Graph refreshed successfully")
            self.workflow_status.setStyleSheet("color: #51cf66; font-style: italic; padding: 5px;")
        except Exception as e:
            self.workflow_status.setText(f"Error refreshing graph: {str(e)}")
            self.workflow_status.setStyleSheet("color: #ff6b6b; font-style: italic; padding: 5px;")
            log.error("Failed to refresh workflow graph: %s", e)
    
    def _toggle_auto_refresh_workflow(self, state: int) -> None:
        """Toggle auto-refresh for the workflow graph."""
        if state == Qt.Checked:
            # Start auto-refresh timer (every 30 seconds)
            if not hasattr(self, '_workflow_refresh_timer'):
                self._workflow_refresh_timer = QTimer()
                self._workflow_refresh_timer.timeout.connect(self._refresh_workflow_graph)
            self._workflow_refresh_timer.start(30000)  # 30 seconds
            self.workflow_status.setText("Auto-refresh enabled (30s interval)")
        else:
            # Stop auto-refresh timer
            if hasattr(self, '_workflow_refresh_timer') and self._workflow_refresh_timer.isActive():
                self._workflow_refresh_timer.stop()
            self.workflow_status.setText("Auto-refresh disabled")
    
    def _export_workflow_graph(self) -> None:
        """Export the workflow graph to an image file."""
        filename, _ = QFileDialog.getSaveFileName(
            self, 
            "Export Workflow Graph", 
            "workflow_graph.png", 
            "PNG Images (*.png);;SVG Images (*.svg);;All Files (*)"
        )
        if filename:
            try:
                # This would depend on the actual implementation of WorkflowGraphWidget
                # For now, we'll show a placeholder message
                QMessageBox.information(self, "Export", f"Workflow graph would be exported to {filename}\n\nNote: Actual export functionality would be implemented in the WorkflowGraphWidget class.")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export workflow graph: {str(e)}")
    
    def _zoom_in_workflow(self) -> None:
        """Zoom in the workflow graph."""
        try:
            self.workflow_graph.zoom_in()
            self.workflow_status.setText("Zoomed in")
        except Exception as e:
            self.workflow_status.setText(f"Error zooming in: {str(e)}")
            self.workflow_status.setStyleSheet("color: #ff6b6b; font-style: italic; padding: 5px;")
    
    def _zoom_out_workflow(self) -> None:
        """Zoom out the workflow graph."""
        try:
            self.workflow_graph.zoom_out()
            self.workflow_status.setText("Zoomed out")
        except Exception as e:
            self.workflow_status.setText(f"Error zooming out: {str(e)}")
            self.workflow_status.setStyleSheet("color: #ff6b6b; font-style: italic; padding: 5px;")
    
    def _reset_workflow_view(self) -> None:
        """Reset the workflow graph view."""
        try:
            self.workflow_graph.reset_view()
            self.workflow_status.setText("View reset")
        except Exception as e:
            self.workflow_status.setText(f"Error resetting view: {str(e)}")
            self.workflow_status.setStyleSheet("color: #ff6b6b; font-style: italic; padding: 5px;")
    
    def _filter_history(self) -> None:
        """Filter run history table by search text."""
        self._update_history_table()
    
    def _update_history_table(self) -> None:
        """Render run summaries in the table."""
        query = (self.history_search.text() or "").lower()
        filtered = []
        selected_source = self.history_source_filter.currentText()
        selected_status = self.history_status_filter.currentText()
        for row in self.run_history:
            haystack = f"{row.run_id} {row.source} {row.status}".lower()
            if query and query not in haystack:
                continue
            if selected_source != "All" and row.source != selected_source:
                continue
            if selected_status != "All" and row.status != selected_status:
                continue
            filtered.append(row)

        total_pages = max(1, (len(filtered) - 1) // self.history_page_size + 1)
        self.history_page = min(self.history_page, total_pages - 1)
        start = self.history_page * self.history_page_size
        end = start + self.history_page_size
        page_rows = filtered[start:end]

        self.history_table.setRowCount(len(page_rows))
        for i, row in enumerate(page_rows):
            meta = row.metadata or {}
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {"raw_metadata": meta}
            item_count = meta.get("item_count")
            error = meta.get("error") or ""
            self.history_table.setItem(i, 0, QTableWidgetItem(row.run_id))
            self.history_table.setItem(i, 1, QTableWidgetItem(row.source))
            status_item = QTableWidgetItem(row.status)
            status_item.setBackground(QColor(self._status_color(row.status)))
            status_item.setForeground(QColor("#ffffff"))
            self.history_table.setItem(i, 2, status_item)
            self.history_table.setItem(i, 3, QTableWidgetItem(self._format_dt(row.started_at)))
            self.history_table.setItem(i, 4, QTableWidgetItem(str(row.duration_seconds or "")))
            self.history_table.setItem(i, 5, QTableWidgetItem("" if item_count is None else str(item_count)))
            self.history_table.setItem(i, 6, QTableWidgetItem(error))
        self.history_page_label.setText(f"Page {self.history_page + 1} / {total_pages}")
        if page_rows:
            self.history_table.selectRow(0)
        else:
            self.history_detail.clear()
            self.history_steps_table.setRowCount(0)
    
    def _load_selected_run_detail(self) -> None:
        """Load detailed info for the selected run and populate detail/steps tables."""
        row_idx = self.history_table.currentRow()
        if row_idx < 0:
            return
        run_id_item = self.history_table.item(row_idx, 0)
        if not run_id_item:
            return
        run_id = run_id_item.text()
        try:
            detail = run_db.fetch_run_detail(run_id)
            steps = run_db.fetch_run_steps(run_id)
        except Exception as exc:
            log.error("Failed to load run detail for %s: %s", run_id, exc)
            return
        
        if not detail:
            self.history_detail.setPlainText("No details available.")
            self.history_steps_table.setRowCount(0)
            return
        
        meta = detail.metadata or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {"raw_metadata": meta}
        stats = detail.stats or {}
        summary_lines = [
            f"Run ID: {detail.run_id}",
            f"Source: {detail.source}",
            f"Status: {detail.status}",
            f"Started: {self._format_dt(detail.started_at)}",
            f"Finished: {self._format_dt(detail.finished_at)}",
            f"Duration (s): {detail.duration_seconds or ''}",
            f"Item count: {meta.get('item_count') or stats.get('records') or ''}",
            f"Output path: {meta.get('output_path', '')}",
        ]
        if meta.get("failed_steps"):
            summary_lines.append(f"Failed steps: {meta.get('failed_steps')}")
        if meta.get("error"):
            summary_lines.append(f"Error: {meta.get('error')}")
        self.history_detail.setPlainText("\n".join(summary_lines))
        
        # Steps table
        self.history_steps_table.setRowCount(len(steps))
        for i, step in enumerate(steps):
            self.history_steps_table.setItem(i, 0, QTableWidgetItem(step.name))
            self.history_steps_table.setItem(i, 1, QTableWidgetItem(step.status))
            self.history_steps_table.setItem(i, 2, QTableWidgetItem(self._format_dt(step.started_at)))
            self.history_steps_table.setItem(i, 3, QTableWidgetItem(str(step.duration_seconds or "")))

        # Update summary cards
        self.summary_status_val.setText(detail.status or "-")
        items_val = meta.get("item_count") or stats.get("records") or ""
        self.summary_items_val.setText(str(items_val) if items_val != "" else "-")
        err_val = meta.get("error") or ""
        if not err_val and meta.get("failed_steps"):
            err_val = "; ".join(f"{k}: {v}" for k, v in meta.get("failed_steps", {}).items())
        self.summary_error_val.setText(err_val or "-")

        # Mirror tasks tab with the same steps
        self._populate_tasks_for_run(run_id)
        self._push_timeline(f"Viewed {run_id}")

    def _open_selected_output(self) -> None:
        """Open the output file for the selected run if available."""
        row_idx = self.history_table.currentRow()
        if row_idx < 0:
            return
        run_id_item = self.history_table.item(row_idx, 0)
        if not run_id_item:
            return
        run_id = run_id_item.text()
        detail = run_db.fetch_run_detail(run_id)
        if not detail:
            return
        meta = detail.metadata or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}
        path = meta.get("output_path")
        if path:
            if not open_path(path):
                QMessageBox.warning(self, "Open Output", f"Could not open {path}")

    def _open_selected_folder(self) -> None:
        """Open the folder containing the output file for the selected run."""
        row_idx = self.history_table.currentRow()
        if row_idx < 0:
            return
        run_id_item = self.history_table.item(row_idx, 0)
        if not run_id_item:
            return
        run_id = run_id_item.text()
        detail = run_db.fetch_run_detail(run_id)
        if not detail:
            return
        meta = detail.metadata or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}
        path = meta.get("output_path")
        if path:
            if not open_parent_folder(path):
                QMessageBox.warning(self, "Open Folder", f"Could not open folder for {path}")

    def _populate_tasks_for_run(self, run_id: str) -> None:
        """Populate tasks tree from run steps."""
        try:
            steps = run_db.fetch_run_steps(run_id)
        except Exception as exc:
            log.error("Failed to load steps for %s: %s", run_id, exc)
            self.tasks_tree.clear()
            return

        self.tasks_tree.clear()
        for step in steps:
            duration = "" if step.duration_seconds is None else str(step.duration_seconds)
            item = QTreeWidgetItem([step.name, step.status, duration, ""])
            self.tasks_tree.addTopLevelItem(item)

    def _populate_run_detail_from_jobs(self, run_id: str) -> None:
        """Update summary cards from a job selection."""
        try:
            detail = run_db.fetch_run_detail(run_id)
        except Exception:
            detail = None
        if not detail:
            return
        meta = detail.metadata or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {"raw_metadata": meta}
        stats = detail.stats or {}
        self.summary_status_val.setText(detail.status or "-")
        items_val = meta.get("item_count") or stats.get("records") or ""
        self.summary_items_val.setText(str(items_val) if items_val != "" else "-")
        err_val = meta.get("error") or ""
        if not err_val and meta.get("failed_steps"):
            err_val = "; ".join(f"{k}: {v}" for k, v in meta.get("failed_steps", {}).items())
        self.summary_error_val.setText(err_val or "-")
    
    def _load_event_history(self) -> None:
        """Backwards compatibility: still load legacy event log into memory (not shown)."""
        history_file = Path("logs/event_history.json")
        if history_file.exists():
            try:
                with open(history_file) as f:
                    self.event_history = json.load(f)
            except Exception as e:
                log.error(f"Failed to load event history: {e}")
    
    def _append_console(self, message: str) -> None:
        """Append message to console output."""
        self.console_output.append(message)
        # Auto-scroll to bottom
        if self.logs_autoscroll:
            scrollbar = self.console_output.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def _append_log_area(self, message: str) -> None:
        """Append message to log text area."""
        if hasattr(self, "logs_text"):
            self.logs_text.append(message)
            sb = self.logs_text.verticalScrollBar()
            sb.setValue(sb.maximum())
        # Add to buffer for filtering
        self.log_buffer.append(
            {
                "text": message,
                "timestamp": datetime.utcnow(),
            }
        )
        self._render_logs()

    def _push_timeline(self, text: str) -> None:
        """Append to timeline list (bounded)."""
        if not hasattr(self, "timeline_list"):
            return
        self.timeline_list.insertItem(0, text)
        while self.timeline_list.count() > 50:
            self.timeline_list.takeItem(self.timeline_list.count() - 1)

    def _on_log_message(self, level: str, message: str) -> None:
        """Handle log message from UI logging handler."""
        self._append_console(f"[{level}] {message}")
        self._append_log_area(f"[{level}] {message}")

    def _render_logs(self) -> None:
        """Render logs with filters."""
        if not hasattr(self, "logs_text"):
            return
        level_filter = (self.log_filter_level.currentText() if hasattr(self, "log_filter_level") else "ALL").upper()
        job_filter = self.log_filter_job.text().strip().lower() if hasattr(self, "log_filter_job") else ""
        module_filter = self.log_filter_module.text().strip().lower() if hasattr(self, "log_filter_module") else ""

        lines = []
        for entry in self.log_buffer[-1000:]:
            text = entry.get("text", "")
            t_lower = text.lower()
            if level_filter != "ALL" and f"[{level_filter}]" not in text.upper():
                continue
            if job_filter and job_filter not in t_lower:
                continue
            if module_filter and module_filter not in t_lower:
                continue
            lines.append(text)
        self.logs_text.setPlainText("\n".join(lines))
        if self.logs_autoscroll:
            sb = self.logs_text.verticalScrollBar()
            sb.setValue(sb.maximum())

    def _history_prev_page(self) -> None:
        if self.history_page > 0:
            self.history_page -= 1
            self._update_history_table()

    def _history_next_page(self) -> None:
        # allow move only if more pages
        query = (self.history_search.text() or "").lower()
        selected_source = self.history_source_filter.currentText()
        selected_status = self.history_status_filter.currentText()
        filtered = []
        for row in self.run_history:
            haystack = f"{row.run_id} {row.source} {row.status}".lower()
            if query and query not in haystack:
                continue
            if selected_source != "All" and row.source != selected_source:
                continue
            if selected_status != "All" and row.status != selected_status:
                continue
            filtered.append(row)
        total_pages = max(1, (len(filtered) - 1) // self.history_page_size + 1)
        if self.history_page < total_pages - 1:
            self.history_page += 1
            self._update_history_table()

    def _on_history_page_size(self, value: str) -> None:
        try:
            self.history_page_size = int(value)
        except ValueError:
            self.history_page_size = 15
        self.history_page = 0
        self._update_history_table()
    
    def _periodic_update(self) -> None:
        """Periodic update of UI elements."""
        # Refresh run history every 10 seconds
        now = datetime.utcnow()
        if not self._last_history_refresh or (now - self._last_history_refresh).total_seconds() > 10:
            self._refresh_run_history()
        # Refresh job statuses
        self.job_manager.poll()
        self._refresh_job_list()

    def _toggle_console_autoscroll(self, state: int) -> None:
        self.logs_autoscroll = state == Qt.Checked

    def _switch_page(self, index: int) -> None:
        """Switch stacked pages via nav buttons."""
        self.main_stack.setCurrentIndex(index)
        self.nav_runs_btn.setChecked(index == 0)
        self.nav_workflow_btn.setChecked(index == 1)
        self.nav_setup_btn.setChecked(index == 2)

    # Styling helpers and summary
    def _styled_nav_button(self, text: str, *, checked: bool = False, on_click=None) -> QPushButton:
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setMinimumHeight(42)
        btn.setStyleSheet(
            """
            QPushButton {
                background-color: #252a3a;
                color: #a0a7b4;
                border: 2px solid #2f3744;
                border-radius: 8px;
                text-align: center;
                padding: 10px 16px;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2d3650;
                border-color: #4f79ff;
                color: #e8e8e8;
            }
            QPushButton:checked {
                background-color: #4f79ff;
                border-color: #7a9bff;
                color: #ffffff;
                font-weight: 700;
            }
            """
        )
        if on_click:
            btn.clicked.connect(on_click)
        self.nav_buttons.addButton(btn)
        return btn

    def _status_chip(self, title: str) -> tuple[QWidget, QLabel]:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #cfd3da; font-size: 11px;")
        lbl_val = QLabel("-")
        lbl_val.setStyleSheet("color: #eaeaea; font-size: 15px; font-weight: 700;")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        return wrapper, lbl_val

    def _status_color(self, status: str) -> str:
        s = (status or "").lower()
        return {
            "running": "#1f7a1f",
            "success": "#1f7a1f",
            "completed": "#4f79ff",
            "failed": "#c0392b",
            "stopped": "#c0392b",
            "partial": "#d4ac0d",
            "pending": "#d4ac0d",
        }.get(s, "#7f8c8d")

    def _bold_font(self):
        f = self.font()
        f.setBold(True)
        return f

    def _create_run_summary(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(16)

        def _card(title: str, color: str = "#8fa3c5"):
            frame = QFrame()
            frame.setFrameShape(QFrame.StyledPanel)
            frame.setStyleSheet(f"""
                background-color: #252a3a;
                border: 2px solid #2f3744;
                border-radius: 10px;
                padding: 12px;
            """)
            v = QVBoxLayout(frame)
            v.setContentsMargins(12, 10, 12, 10)
            lbl_title = QLabel(title)
            lbl_title.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 600;")
            lbl_val = QLabel("-")
            lbl_val.setStyleSheet("color: #e8e8e8; font-size: 20px; font-weight: 700;")
            lbl_val.setAlignment(Qt.AlignCenter)
            v.addWidget(lbl_title, 0, Qt.AlignCenter)
            v.addWidget(lbl_val)
            v.addStretch()
            return frame, lbl_val

        self.summary_status_card, self.summary_status_val = _card("Status", "#4f79ff")
        self.summary_items_card, self.summary_items_val = _card("Items", "#51cf66")
        self.summary_error_card, self.summary_error_val = _card("Last Error", "#ff6b6b")
        self.summary_error_val.setWordWrap(True)
        self.summary_error_val.setStyleSheet("color: #ff6b6b; font-size: 14px; font-weight: 600;")

        layout.addWidget(self.summary_status_card)
        layout.addWidget(self.summary_items_card)
        layout.addWidget(self.summary_error_card)
        return widget

    def _setup_status_items(self):
        snapshot = self.setup_snapshot or {}
        env = os.getenv("SCRAPER_PLATFORM_ENV") or os.getenv("ENV") or "prod"

        secret_key_env = bool(os.getenv("SCRAPER_SECRET_KEY"))
        key_file = Path(os.getenv("SCRAPER_SECRET_KEY_FILE", _DEFAULT_KEY_PATH))
        secret_key_file = key_file.exists()

        run_storage = snapshot.get("storage") or run_db.initialize_run_storage()
        backend = (run_storage or {}).get("backend", "unknown")
        location = (run_storage or {}).get("location", "not configured")
        run_db_ok = backend in {"sqlite", "postgres"}

        required_dir_paths = [Path(p) for p in snapshot.get("required_dirs", [])] or [
            Path("sessions"),
            Path("sessions/cookies"),
            Path("sessions/logs"),
            Path("output"),
            Path("input"),
            Path("logs"),
        ]
        dirs_ok = all(p.exists() for p in required_dir_paths)
        missing_dirs = [str(p) for p in required_dir_paths if not p.exists()]

        airflow_installed = snapshot.get("airflow_installed")
        if airflow_installed is None:
            airflow_installed = self.airflow_service.is_airflow_installed()

        fake_browser = os.getenv("SCRAPER_PLATFORM_FAKE_BROWSER")
        items = [
            (f"Environment: {env}", True),
            (f"Secret key (env): {'set' if secret_key_env else 'missing'}", secret_key_env),
            (f"Secret key file: {'present' if secret_key_file else 'missing'} ({key_file})", secret_key_file),
            (f"Run tracking storage: {backend} ({location})", run_db_ok),
            (f"Required folders present: {'all created' if dirs_ok else 'missing: ' + ', '.join(missing_dirs)}", dirs_ok),
            (f"Airflow installed: {'yes' if airflow_installed else 'no'}", bool(airflow_installed)),
            (f"Fake browser: {'on' if fake_browser else 'off'}", True),
        ]
        return items

    def _setup_instructions_html(self, items) -> str:
        missing = [text for text, ok in items if not ok]
        missing_html = "".join(f"<li>{text}</li>" for text in missing) or "<li>All good.</li>"
        auto_db_note = ""
        if self.setup_snapshot.get("run_db_path"):
            auto_db_note = f"<li>Configured local run-tracking SQLite at {self.setup_snapshot['run_db_path']}</li>"
        auto_key_note = ""
        if self.setup_snapshot.get("generated_key"):
            auto_key_note = f"<li>Generated a secret key at {self.setup_snapshot['generated_key']}</li>"
        return f"""
        <h3>How to complete setup</h3>
        <ul>
            <li>Set <code>SCRAPER_SECRET_KEY</code> (or use generated key at {_DEFAULT_KEY_PATH}).</li>
            <li>Configure run tracking: set <code>DB_URL</code> or <code>RUN_DB_PATH</code>.</li>
            <li>Environment: ensure <code>SCRAPER_PLATFORM_ENV</code> or <code>ENV</code> is correct.</li>
            <li>Optional: <code>SCRAPER_PLATFORM_FAKE_BROWSER=1</code> for headless fake driver.</li>
            <li>Install dependencies: <code>pip install -r requirements.txt</code> (desktop UI) and run Airflow where applicable.</li>
            {auto_db_note}
            {auto_key_note}
        </ul>
        <p><b>Missing or needs attention:</b></p>
        <ul>{missing_html}</ul>
        """
    
    def _export_logs(self) -> None:
        """Export logs to file."""
        filename, _ = QFileDialog.getSaveFileName(self, "Export Logs", "", "Text Files (*.txt)")
        if filename:
            with open(filename, 'w') as f:
                f.write(self.logs_text.toPlainText())
            QMessageBox.information(self, "Export Complete", f"Logs exported to {filename}")
    
    def _show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Scraper Platform",
            "Scraper Platform Desktop Application\n\n"
            "Version 5.0\n"
            "A comprehensive scraping and automation platform."
        )
    
    def closeEvent(self, event) -> None:
        """Handle window close event."""
        # Save event history
        history_file = Path("logs/event_history.json")
        history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(history_file, 'w') as f:
            json.dump(self.event_history, f, indent=2, default=str)
        
        # Stop any running pipelines
        if self.pipeline_runner:
            self.pipeline_runner.cancel()
            self.pipeline_runner.wait()
        
        # Stop Airflow services
        if self.airflow_service.is_running():
            reply = QMessageBox.question(
                self,
                "Stop Airflow Services?",
                "Airflow services are running. Stop them before closing?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self.airflow_service.stop_all()
        
        event.accept()


def main() -> int:
    """Main entry point for the desktop application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Scraper Platform")
    app.setOrganizationName("Scraper Platform")
    
    window = MainWindow()
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

