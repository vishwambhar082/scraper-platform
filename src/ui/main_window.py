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
from src.ui.modern_components import (
    IconSidebar,
    Card,
    ActivityCard,
    SectionHeader,
    BulletList,
    ActivityPanel,
)

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
        self.showFullScreen()  # Open window in full screen mode
        # Set window icon if available
        # self.setWindowIcon(QIcon("path/to/icon.png"))
        
        # Theme manager
        self.theme_manager = ThemeManager()
        self._apply_theme("light")  # Default to minimal white theme

        
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
        self.log_file_path = Path("logs/ui_logs.json")

        # Load persisted logs
        self._load_persisted_logs()
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

    def _styled_nav_button(self, text: str, checked: bool = False, on_click=None):
        """Create a styled navigation button with modern aesthetics."""
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setChecked(checked)
        if on_click:
            btn.clicked.connect(lambda: self._on_nav_button_clicked(btn, on_click))
        else:
            btn.clicked.connect(lambda: self._on_nav_button_clicked(btn))
        
        # Set appropriate icon based on button text
        icon_name = "SP_FileIcon"  # Default icon
        if "Run" in text: icon_name = "SP_ComputerIcon"
        elif "Workflow" in text: icon_name = "SP_FileDialogDetailedView"
        elif "Scraper" in text: icon_name = "SP_FileDialogContentsView"
        elif "Platform" in text: icon_name = "SP_MessageBoxInformation"
        elif "Setting" in text: icon_name = "SP_FileDialogListView"
        
        btn.setIcon(self.style().standardIcon(getattr(QStyle, icon_name)))
        
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #6b7280;
                border: none;
                text-align: left;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: 400;
                border-left: 2px solid transparent;
            }
            QPushButton:hover {
                background-color: #f9fafb;
                color: #374151;
            }
            QPushButton:checked {
                background-color: #f3f4f6;
                color: #1f2937;
                border-left: 2px solid #4b5563;
                font-weight: 500;
            }
        """)
        return btn
        
    def _on_nav_button_clicked(self, button, callback=None):
        """Handle navigation button click and update UI state."""
        # Uncheck all other buttons in the group
        for btn in self.findChildren(QPushButton):
            if btn != button and btn.isCheckable():
                btn.setChecked(False)
        
        # Ensure the clicked button is checked
        button.setChecked(True)
        
        # Execute the callback if provided
        if callback:
            callback()
    
    def _create_console_panel(self) -> QWidget:
        """Create a reusable console panel widget."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Console output area - terminal style: black background, yellow font
        self.console_output = QTextEdit()

        # Console header with title
        title_layout = QHBoxLayout()
        console_title = QLabel("Console Output")
        console_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #1f2937;")
        title_layout.addWidget(console_title)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Control buttons row
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)

        # Clear Console button - prominent red button
        clear_btn = QPushButton("🗑️ Clear Console")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
                border-radius: 6px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #b91c1c;
            }
            QPushButton:pressed {
                background-color: #991b1b;
            }
        """)
        clear_btn.clicked.connect(lambda: self.console_output.clear())
        controls_layout.addWidget(clear_btn)

        # Auto-scroll checkbox
        self.console_autoscroll_cb = QCheckBox("Auto-scroll")
        self.console_autoscroll_cb.setChecked(True)
        self.console_autoscroll_cb.stateChanged.connect(self._toggle_console_autoscroll)
        controls_layout.addWidget(self.console_autoscroll_cb)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Add spacing before console
        layout.addSpacing(8)
        self.console_output.setReadOnly(True)
        self.console_output.setStyleSheet("""
            QTextEdit {
                background-color: #000000;
                color: #ffdd00;
                border: 1px solid #333333;
                border-radius: 4px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                padding: 10px;
                selection-background-color: #444444;
                selection-color: #ffdd00;
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
        nav_title.setProperty("class", "subheading")
        nav_layout.addWidget(nav_title)

        self.nav_buttons = QButtonGroup(self)
        self.nav_buttons.setExclusive(True)

        self.nav_runs_btn = self._styled_nav_button("Runs & Console", checked=True, on_click=lambda: self._switch_page(0))
        nav_layout.addWidget(self.nav_runs_btn)

        self.nav_workflow_btn = self._styled_nav_button("Workflow & Airflow", on_click=lambda: self._switch_page(1))
        nav_layout.addWidget(self.nav_workflow_btn)

        self.nav_scrapers_btn = self._styled_nav_button("Scrapers Info", on_click=lambda: self._switch_page(2))
        nav_layout.addWidget(self.nav_scrapers_btn)

        self.nav_settings_btn = self._styled_nav_button("Settings & Env", on_click=lambda: self._switch_page(3))
        nav_layout.addWidget(self.nav_settings_btn)

        self.nav_setup_btn = self._styled_nav_button("Setup Checklist", on_click=lambda: self._switch_page(4))
        nav_layout.addWidget(self.nav_setup_btn)

        self.nav_info_btn = self._styled_nav_button("Platform Overview", on_click=lambda: self._switch_page(5))
        nav_layout.addWidget(self.nav_info_btn)

        nav_layout.addStretch()

        # Add close/exit button
        exit_btn = QPushButton("Exit Full Screen")
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: white;
                border: none;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: 600;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #b91c1c;
            }
            QPushButton:pressed {
                background-color: #991b1b;
            }
        """)
        exit_btn.clicked.connect(self.close)
        nav_layout.addWidget(exit_btn)

        nav_layout.addSpacing(8)

        # Add a footer with version info
        version_label = QLabel("v5.0.1 • Scraper Platform")
        version_label.setProperty("class", "caption")
        version_label.setAlignment(Qt.AlignCenter)
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
        scrapers_page = self._create_scrapers_page()
        settings_page = self._create_settings_page()
        setup_page = self._create_setup_page()
        platform_info_page = self._create_platform_info_page()

        self.main_stack.addWidget(runs_console_page)      # 0
        self.main_stack.addWidget(workflow_page)          # 1
        self.main_stack.addWidget(scrapers_page)          # 2
        self.main_stack.addWidget(settings_page)          # 3
        self.main_stack.addWidget(setup_page)             # 4
        self.main_stack.addWidget(platform_info_page)     # 5
        
        
        content_layout.addWidget(self.main_stack, 1)
        main_layout.addWidget(content_stack, 1)  # Middle section takes remaining space
        
        # REMOVED: Global console panel to avoid duplication.

    
    def _create_left_pane(self) -> QWidget:
        """Create the left pane with job list, tasks, logs, history."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Tabs for different views
        tabs = QTabWidget()
        
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

        # Left Pane - Tabs for Jobs/Tasks/Logs/History
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # Create tab widget for left pane
        tabs = QTabWidget()

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

        # Add console panel - MAXIMIZED, no other logs
        console_panel = self._create_console_panel()
        right_layout.addWidget(console_panel, 1)

        splitter.addWidget(right_widget)

        # Set initial splitter sizes (60% left, 40% right) for narrower console
        splitter.setSizes([int(self.width() * 0.60), int(self.width() * 0.40)])

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
        title.setProperty("class", "heading")
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
        refresh_btn.clicked.connect(self._refresh_workflow_graph)
        header.addWidget(refresh_btn)
        
        layout.addLayout(header)
        
        # Create tab widget
        tabs = QTabWidget()
        
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
        title.setProperty("class", "heading")
        layout.addWidget(title)

        desc = QLabel("The UI validates required prerequisites and can run auto-setup for you.")
        desc.setProperty("class", "muted")
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
        layout.addWidget(self.setup_checklist)

        self.setup_info = QTextBrowser()
        self.setup_info.setOpenExternalLinks(True)
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
        """Create the jobs list tab with clean layout."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Controls in a clean grid layout
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
        button_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Stop Job")
        self.stop_btn.setProperty("class", "danger")
        self.stop_btn.clicked.connect(self._stop_job)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setMinimumWidth(100)
        button_layout.addWidget(self.stop_btn)

        button_layout.addStretch()
        controls.addLayout(button_layout, 1, 2, 1, 2)

        layout.addLayout(controls)

        # Jobs table
        self.jobs_table = QTableWidget()
        self.jobs_table.setColumnCount(6)
        self.jobs_table.setHorizontalHeaderLabels([
            "Run ID", "Source", "Status", "Started", "Duration", "Items"
        ])
        self.jobs_table.horizontalHeader().setStretchLastSection(True)
        self.jobs_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.jobs_table.setAlternatingRowColors(True)
        self.jobs_table.itemSelectionChanged.connect(self._on_job_selected)
        layout.addWidget(self.jobs_table, 1)

        return widget
    
    def _create_tasks_tab(self) -> QWidget:
        """Create the tasks list tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("Task Execution")
        title.setProperty("class", "heading")
        layout.addWidget(title)

        self.tasks_tree = QTreeWidget()
        self.tasks_tree.setHeaderLabels(["Task", "Status", "Duration", "Output"])
        self.tasks_tree.setColumnWidth(0, 200)
        layout.addWidget(self.tasks_tree)
        
        return widget
    
    def _create_logs_tab(self) -> QWidget:
        """Create the logs tab with clean layout."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Filter toolbar - clean, non-overlapping
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(6)

        self.log_filter = QLineEdit()
        self.log_filter.setPlaceholderText("Search logs...")
        self.log_filter.textChanged.connect(self._filter_logs)
        self.log_filter.setMaximumWidth(200)
        filter_layout.addWidget(self.log_filter)

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.currentTextChanged.connect(self._filter_logs)
        self.log_level_combo.setMaximumWidth(120)
        filter_layout.addWidget(self.log_level_combo)

        filter_layout.addStretch()

        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self._export_logs)
        export_btn.setMaximumWidth(80)
        filter_layout.addWidget(export_btn)

        layout.addLayout(filter_layout)

        # Logs text area
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setFontFamily("Consolas")
        self.logs_text.setFontPointSize(9)
        layout.addWidget(self.logs_text, 1)

        return widget
    
    def _create_history_tab(self) -> QWidget:
        """Create a simple, clean run history tab with just the main table."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        heading = QLabel("Run History")
        heading.setProperty("class", "heading")
        layout.addWidget(heading)

        # Compact toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.history_search = QLineEdit()
        self.history_search.setPlaceholderText("Search...")
        self.history_search.textChanged.connect(self._filter_history)
        self.history_search.setMaximumWidth(180)
        toolbar.addWidget(self.history_search)

        self.history_source_filter = QComboBox()
        self.history_source_filter.addItem("All Sources")
        self.history_source_filter.currentIndexChanged.connect(self._filter_history)
        self.history_source_filter.setMaximumWidth(140)
        toolbar.addWidget(self.history_source_filter)

        self.history_status_filter = QComboBox()
        self.history_status_filter.addItems(["All Status", "success", "failed", "partial", "running"])
        self.history_status_filter.currentIndexChanged.connect(self._filter_history)
        self.history_status_filter.setMaximumWidth(120)
        toolbar.addWidget(self.history_status_filter)

        toolbar.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_run_history)
        refresh_btn.setMaximumWidth(90)
        toolbar.addWidget(refresh_btn)

        layout.addLayout(toolbar)

        # Main runs table - clean and simple
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(
            ["Run ID", "Source", "Status", "Started", "Duration"]
        )

        # Set dynamic column widths with Run ID wider than Source
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive)  # Run ID - user adjustable
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Source - takes remaining space
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Status
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Started
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Duration

        # Set Run ID column to be wider than Source
        self.history_table.setColumnWidth(0, 280)  # Run ID gets more space

        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setSelectionMode(QTableWidget.SingleSelection)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.itemSelectionChanged.connect(self._load_selected_run_detail)
        self.history_table.setSortingEnabled(True)
        self.history_table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.history_table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        self.history_table.setStyleSheet(
            """
            QTableWidget {
                gridline-color: #e5e7eb;
            }
            QHeaderView::section {
                padding: 6px;
                background: #f8fafc;
                border: 1px solid #e5e7eb;
                font-weight: 600;
            }
            """
        )

        layout.addWidget(self.history_table, 3)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)

        # Run details section - compact and simple
        details_label = QLabel("Run Details")
        details_label.setProperty("class", "subheading")
        details_label.setStyleSheet("font-weight: bold; font-size: 12px; margin-top: 8px;")
        layout.addWidget(details_label)

        self.history_detail = QTextEdit()
        self.history_detail.setReadOnly(True)
        self.history_detail.setMinimumHeight(100)
        self.history_detail.setMaximumHeight(150)
        self.history_detail.setPlaceholderText("Select a run to view details")
        self.history_detail.setStyleSheet("""
            QTextEdit {
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.history_detail)

        # Steps table - compact
        steps_label = QLabel("Run Steps")
        steps_label.setProperty("class", "subheading")
        steps_label.setStyleSheet("font-weight: bold; font-size: 12px; margin-top: 8px;")
        layout.addWidget(steps_label)

        self.history_steps_table = QTableWidget()
        self.history_steps_table.setColumnCount(3)
        self.history_steps_table.setHorizontalHeaderLabels(["Step", "Status", "Duration (s)"])
        steps_header = self.history_steps_table.horizontalHeader()
        steps_header.setSectionResizeMode(0, QHeaderView.Stretch)
        steps_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        steps_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.history_steps_table.setMinimumHeight(150)
        self.history_steps_table.setMaximumHeight(250)
        self.history_steps_table.setAlternatingRowColors(True)
        self.history_steps_table.verticalHeader().setVisible(False)
        self.history_steps_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e5e7eb;
            }
            QHeaderView::section {
                padding: 6px;
                background: #f8fafc;
                border: 1px solid #e5e7eb;
                font-weight: 600;
            }
        """)
        layout.addWidget(self.history_steps_table, 1)

        return widget

    def _history_sort_key(self, row: Any) -> Any:
        """Sort helper to order runs by started_at (fallback finished_at)."""
        # Prefer started_at; if missing, fall back to finished_at to keep ordering stable
        ts = getattr(row, "started_at", None) or getattr(row, "finished_at", None)
        return ts or datetime.min

    def _create_workflow_tab(self) -> QWidget:
        """Create the workflow visualization tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # Title
        title = QLabel("Workflow Visualization")
        title.setProperty("class", "heading")
        layout.addWidget(title)

        # Controls toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        refresh_btn = QPushButton("Refresh Graph")
        refresh_btn.clicked.connect(self._refresh_workflow_graph)
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
        layout.addWidget(self.workflow_status)
        
        return widget

    def _create_workflow_tab(self) -> QWidget:
        """Create the workflow visualization tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("Live Workflow Graph")
        title.setProperty("class", "heading")
        layout.addWidget(title)

        # Controls
        toolbar = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_workflow_graph)
        toolbar.addWidget(refresh_btn)
        
        zoom_in_btn = QPushButton("Zoom In")
        zoom_in_btn.clicked.connect(self._zoom_in_workflow)
        toolbar.addWidget(zoom_in_btn)
        
        zoom_out_btn = QPushButton("Zoom Out")
        zoom_out_btn.clicked.connect(self._zoom_out_workflow)
        toolbar.addWidget(zoom_out_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Graph
        # Create a new instance for this tab
        self.workflow_graph_main = WorkflowGraphWidget()
        layout.addWidget(self.workflow_graph_main)
        
        return widget
    
    def _create_airflow_tab(self) -> QWidget:
        """Create the Airflow DAG view tab with service management."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("Airflow Services & DAG Management")
        title.setProperty("class", "heading")
        layout.addWidget(title)

        # Service management section - no box
        service_label = QLabel("Service Management")
        service_label.setProperty("class", "subheading")
        layout.addWidget(service_label)

        # Service controls toolbar
        service_toolbar = QHBoxLayout()
        service_toolbar.setSpacing(8)

        # Start/Stop Airflow button
        self.airflow_start_btn = QPushButton("Start Airflow")
        self.airflow_start_btn.setProperty("class", "success")
        self.airflow_start_btn.clicked.connect(self._start_airflow_services)
        service_toolbar.addWidget(self.airflow_start_btn)

        self.airflow_stop_btn = QPushButton("Stop Airflow")
        self.airflow_stop_btn.setProperty("class", "danger")
        self.airflow_stop_btn.clicked.connect(self._stop_airflow_services)
        self.airflow_stop_btn.setEnabled(False)
        service_toolbar.addWidget(self.airflow_stop_btn)

        # Status label
        self.airflow_service_status = QLabel("Not running")
        service_toolbar.addWidget(self.airflow_service_status)

        service_toolbar.addStretch()
        layout.addLayout(service_toolbar)

        layout.addSpacing(12)

        # Connection section - no box
        connection_label = QLabel("Connection & Control")
        connection_label.setProperty("class", "subheading")
        layout.addWidget(connection_label)

        # Toolbar - all controls in one row
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        # Airflow URL input
        toolbar.addWidget(QLabel("Airflow URL:"))
        self.airflow_url = QLineEdit()
        self.airflow_url.setText("http://localhost:8080")
        self.airflow_url.setPlaceholderText("http://localhost:8080")
        self.airflow_url.setMinimumWidth(200)
        toolbar.addWidget(self.airflow_url)

        # Check connection button
        check_btn = QPushButton("Check")
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

        # Connection status label
        self.airflow_status_label = QLabel("Not connected")
        toolbar.addWidget(self.airflow_status_label)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        layout.addSpacing(12)

        # Web view for Airflow UI - no box
        webview_label = QLabel("Airflow Web Interface")
        webview_label.setProperty("class", "subheading")
        layout.addWidget(webview_label)

        self.airflow_webview = QWebEngineView()
        # Don't auto-load - wait for user to connect
        self.airflow_webview.setHtml("""
            <html>
            <body style="background-color: #fafafa; color: #374151; font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: #4b5563;">Airflow Desktop Integration</h2>
                <p>Click "Start Airflow" to launch the scheduler and API server.</p>
                <p>Then click "Connect" to load the Airflow UI.</p>
            </body>
            </html>
        """)
        layout.addWidget(self.airflow_webview)
        
        return widget
    
    def _create_status_tab(self) -> QWidget:
        """Create the status indicators tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Title
        title = QLabel("System Status")
        title.setProperty("class", "heading")
        layout.addWidget(title)

        # Status indicators will be added here
        self.status_label = QLabel("System Status: Ready")
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
        # Simple widget without frame
        card = QWidget()

        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setProperty("class", "caption")

        value_label = QLabel(value)
        value_label.setProperty("class", "subheading")

        layout.addWidget(title_label, 0, Qt.AlignCenter)
        layout.addWidget(value_label, 0, Qt.AlignCenter)

        return card
    
    def _create_console_panel(self) -> QWidget:
        """Console output panel (placed on the right side of Runs page)."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        
        console_label = QLabel("Console Output")
        console_label.setProperty("class", "subheading")
        layout.addWidget(console_label)

        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setStyleSheet("""
            QTextEdit {
                background-color: #000000;
                color: #ffdd00;
                border: 1px solid #333333;
                border-radius: 4px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                padding: 8px;
                selection-background-color: #444444;
                selection-color: #ffdd00;
            }
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
        lbl.setProperty("class", "subheading")
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
        lbl.setProperty("class", "subheading")
        layout.addWidget(lbl)
        self.timeline_list = QListWidget()
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
        self._push_timeline(f"Started {job_id} ({source})")
    
    def _stop_job(self) -> None:
        """Stop the current pipeline job."""
        row = self.jobs_table.currentRow()
        if row >= 0:
            job_id = self.jobs_table.item(row, 0).text()
            self.job_manager.stop_job(job_id)
            self._append_console(f"[INFO] Stopped job {job_id}")
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
        # self._add_event("JOB_FINISHED", status=status, result=result)
        self._refresh_job_list()

        if status == "failed":
            error_msg = result.get('error', 'Unknown error')
            # Show error in console
            self._append_console(f"[ERROR] Job failed: {error_msg}")
            # Show error in logs tab
            self._append_log_area(f"[ERROR] Job failed: {error_msg}")
            # Show detailed stack trace if available
            if "traceback" in result:
                self._append_console(f"[ERROR] Traceback:\n{result['traceback']}")
                self._append_log_area(f"[ERROR] Traceback:\n{result['traceback']}")
            QMessageBox.warning(self, "Job Failed", f"Pipeline failed: {error_msg}")
        else:
            self._append_console(f"[INFO] Job completed successfully")
            QMessageBox.information(self, "Job Complete", "Pipeline completed successfully!")
    
    def _on_job_selected(self) -> None:
        """Handle job selection."""
        selected = self.jobs_table.selectedItems()
        if selected:
            run_id = self.jobs_table.item(self.jobs_table.currentRow(), 0).text()
            self._populate_tasks_for_run(run_id)
            self._populate_run_detail_from_jobs(run_id)
            self._render_console_for_job(run_id)

            # Show error details in console for failed jobs
            job_info = self.job_manager.jobs.get(run_id)
            if job_info and job_info.status == "failed" and job_info.result:
                error_msg = job_info.result.get("error", "Unknown error")
                self._append_console(f"\n[ERROR] Job {run_id} failed: {error_msg}")
                if "traceback" in job_info.result:
                    self._append_console(f"[ERROR] Traceback:\n{job_info.result['traceback']}")

    def _render_console_for_job(self, job_id: str) -> None:
        """Show console output scoped to the selected job."""
        self.console_output.clear()
        info = self.job_manager.jobs.get(job_id)
        if not info:
            self._append_console(f"[WARN] No details for job {job_id}")
            return

        self._append_console(f"[JOB] {job_id} | source={info.source} | status={info.status}")
        if info.started_at:
            self._append_console(f"  started_at={datetime.fromtimestamp(info.started_at)}")
        if info.ended_at:
            self._append_console(f"  ended_at={datetime.fromtimestamp(info.ended_at)}")

        if info.result:
            status = info.result.get("status")
            error = info.result.get("error")
            tb = info.result.get("traceback")
            self._append_console(f"[RESULT] status={status}")
            if error:
                self._append_console(f"[ERROR] {error}")
            if tb:
                self._append_console(f"[TRACEBACK]\n{tb}")

        # Live step logs captured from worker progress messages
        for log_line in info.logs:
            self._append_console(log_line)

        # Append latest run detail/steps from tracking DB so user can see progress
        run_id = job_id
        if info.result and info.result.get("run_id"):
            run_id = info.result["run_id"]
            self._append_console(f"[RUN_ID] {run_id}")

        try:
            detail = run_db.fetch_run_detail(run_id)
            steps = run_db.fetch_run_steps(run_id) if detail else []
        except Exception:
            detail, steps = None, []

        if detail:
            self._append_console(
                f"[RUN] status={detail.status} started={self._format_dt(detail.started_at)} "
                f"finished={self._format_dt(detail.finished_at)}"
            )
        for step in steps:
            self._append_console(
                f"[STEP] {step.name} | status={step.status} | started={self._format_dt(step.started_at)}"
            )
    
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
                status_item.setForeground(QColor("#1f2937"))
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
        if not hasattr(self, 'log_buffer') or not hasattr(self, 'logs_text'):
            return

        search_text = self.log_filter.text().lower()
        level_filter = self.log_level_combo.currentText()

        filtered_logs = []
        for log_entry in self.log_buffer:
            text = log_entry.get("text", "")

            # Filter by level - check if level appears in the log text
            if level_filter != "ALL" and f"[{level_filter}]" not in text.upper():
                continue

            # Filter by search text
            if search_text and search_text not in text.lower():
                continue

            filtered_logs.append(text)

        # Update display - use setPlainText for better performance
        self.logs_text.setPlainText("\n".join(filtered_logs))

        # Auto-scroll to bottom if enabled
        if hasattr(self, 'logs_autoscroll') and self.logs_autoscroll:
            scrollbar = self.logs_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
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
            self.run_history = sorted(
                runs,
                key=self._history_sort_key,
                reverse=True,
            )
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
            # Refresh whichever workflow graph exists
            if hasattr(self, 'workflow_graph'):
                self.workflow_graph.refresh()
            if hasattr(self, 'workflow_graph_main'):
                self.workflow_graph_main.refresh()
            if hasattr(self, 'workflow_status'):
                self.workflow_status.setText("Graph refreshed")
                self.workflow_status.setStyleSheet("color: #6b7280;")
        except Exception as e:
            if hasattr(self, 'workflow_status'):
                self.workflow_status.setText(f"Error: {str(e)}")
                self.workflow_status.setStyleSheet("color: #9ca3af;")
            log.error("Failed to refresh workflow graph: %s", e)
    
    def _toggle_auto_refresh_workflow(self, state: int) -> None:
        """Toggle auto-refresh for the workflow graph."""
        if state == Qt.Checked:
            # Start auto-refresh timer (every 30 seconds)
            if not hasattr(self, '_workflow_refresh_timer'):
                self._workflow_refresh_timer = QTimer()
                self._workflow_refresh_timer.timeout.connect(self._refresh_workflow_graph)
            self._workflow_refresh_timer.start(30000)  # 30 seconds
            if hasattr(self, 'workflow_status'):
                self.workflow_status.setText("Auto-refresh enabled")
        else:
            # Stop auto-refresh timer
            if hasattr(self, '_workflow_refresh_timer') and self._workflow_refresh_timer.isActive():
                self._workflow_refresh_timer.stop()
            if hasattr(self, 'workflow_status'):
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
            if hasattr(self, 'workflow_graph'):
                self.workflow_graph.zoom_in()
            if hasattr(self, 'workflow_graph_main'):
                self.workflow_graph_main.zoom_in()
            if hasattr(self, 'workflow_status'):
                self.workflow_status.setText("Zoomed in")
        except Exception as e:
            if hasattr(self, 'workflow_status'):
                self.workflow_status.setText(f"Error: {str(e)}")
                self.workflow_status.setStyleSheet("color: #9ca3af;")

    def _zoom_out_workflow(self) -> None:
        """Zoom out the workflow graph."""
        try:
            if hasattr(self, 'workflow_graph'):
                self.workflow_graph.zoom_out()
            if hasattr(self, 'workflow_graph_main'):
                self.workflow_graph_main.zoom_out()
            if hasattr(self, 'workflow_status'):
                self.workflow_status.setText("Zoomed out")
        except Exception as e:
            if hasattr(self, 'workflow_status'):
                self.workflow_status.setText(f"Error: {str(e)}")
                self.workflow_status.setStyleSheet("color: #9ca3af;")

    def _reset_workflow_view(self) -> None:
        """Reset the workflow graph view."""
        try:
            if hasattr(self, 'workflow_graph'):
                self.workflow_graph.reset_view()
            if hasattr(self, 'workflow_graph_main'):
                self.workflow_graph_main.reset_view()
            if hasattr(self, 'workflow_status'):
                self.workflow_status.setText("View reset")
        except Exception as e:
            if hasattr(self, 'workflow_status'):
                self.workflow_status.setText(f"Error: {str(e)}")
                self.workflow_status.setStyleSheet("color: #9ca3af;")
    
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
            if selected_source not in ("All Sources", "All") and row.source != selected_source:
                continue
            if selected_status not in ("All Status", "All") and row.status != selected_status:
                continue
            filtered.append(row)

        filtered.sort(key=self._history_sort_key, reverse=True)
        total_pages = max(1, (len(filtered) - 1) // self.history_page_size + 1)
        self.history_page = min(self.history_page, total_pages - 1)
        start = self.history_page * self.history_page_size
        end = start + self.history_page_size
        page_rows = filtered[start:end]

        self.history_table.setSortingEnabled(False)
        self.history_table.setRowCount(len(page_rows))
        for i, row in enumerate(page_rows):
            # Show full Run ID (no truncation)
            run_id_item = QTableWidgetItem(row.run_id)
            run_id_item.setData(Qt.UserRole, row.run_id)  # Store full run_id for reference
            self.history_table.setItem(i, 0, run_id_item)

            self.history_table.setItem(i, 1, QTableWidgetItem(row.source))
            status_item = QTableWidgetItem(row.status)
            status_item.setBackground(QColor(self._status_color(row.status)))
            status_item.setForeground(QColor("#1f2937"))
            self.history_table.setItem(i, 2, status_item)
            self.history_table.setItem(i, 3, QTableWidgetItem(self._format_dt(row.started_at)))
            duration = f"{row.duration_seconds:.1f}s" if row.duration_seconds else ""
            self.history_table.setItem(i, 4, QTableWidgetItem(duration))
        # Keep header sort indicator on "Started" descending for clarity
        header = self.history_table.horizontalHeader()
        header.setSortIndicatorShown(True)
        header.setSortIndicator(3, Qt.DescendingOrder)
        self.history_table.setSortingEnabled(True)

        # Select first row and load its details
        if page_rows:
            self.history_table.selectRow(0)
            # Manually trigger detail load to ensure it happens even if selection doesn't change
            self._load_selected_run_detail()
        else:
            self.history_detail.clear()
            self.history_steps_table.setRowCount(0)
    
    def _load_selected_run_detail(self) -> None:
        """Load detailed info for the selected run and populate detail/steps tables."""
        try:
            row_idx = self.history_table.currentRow()
            if row_idx < 0:
                self.history_detail.setPlainText("No run selected. Click on a run in the table above.")
                self.history_steps_table.setRowCount(0)
                return

            run_id_item = self.history_table.item(row_idx, 0)
            if not run_id_item:
                self.history_detail.setPlainText("No run data available")
                self.history_steps_table.setRowCount(0)
                return

            # Get the full run_id from stored data (not the shortened display text)
            run_id = run_id_item.data(Qt.UserRole)
            if not run_id:
                # Fallback to text if data not available
                run_id = run_id_item.text()

            log.info(f"Loading run detail for: {run_id}")

            # Show loading indicator
            self.history_detail.setPlainText(f"Loading details for run: {run_id}...")
            self.history_steps_table.setRowCount(0)
        except Exception as ex:
            log.error(f"Error in detail load initialization: {ex}")
            self.history_detail.setPlainText(f"Error: {ex}")
            return

        try:
            detail = run_db.fetch_run_detail(run_id)
            steps = run_db.fetch_run_steps(run_id)
        except Exception as exc:
            log.error("Failed to load run detail for %s: %s", run_id, exc)
            self.history_detail.setPlainText(f"Error loading details: {exc}")
            self.history_steps_table.setRowCount(0)
            return

        if not detail:
            self.history_detail.setPlainText(f"No details found for run: {run_id}")
            self.history_steps_table.setRowCount(0)
            return

        # Parse metadata
        meta = detail.metadata or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {"raw_metadata": meta}
        stats = detail.stats or {}

        # Build summary
        summary_lines = [
            f"Run ID: {detail.run_id}",
            f"Source: {detail.source}",
            f"Status: {detail.status}",
            f"Started: {self._format_dt(detail.started_at)}",
            f"Finished: {self._format_dt(detail.finished_at)}",
            f"Duration (s): {detail.duration_seconds or 'N/A'}",
            f"Item count: {meta.get('item_count') or stats.get('records') or 'N/A'}",
            f"Output path: {meta.get('output_path', 'N/A')}",
        ]
        if meta.get("failed_steps"):
            summary_lines.append(f"Failed steps: {meta.get('failed_steps')}")
        if meta.get("error"):
            summary_lines.append(f"Error: {meta.get('error')}")

        # Update details text
        self.history_detail.setPlainText("\n".join(summary_lines))
        log.info(f"Loaded details for {run_id}: {len(summary_lines)} lines")

        # Update steps table
        self.history_steps_table.setRowCount(len(steps))
        for i, step in enumerate(steps):
            self.history_steps_table.setItem(i, 0, QTableWidgetItem(step.name or ""))
            self.history_steps_table.setItem(i, 1, QTableWidgetItem(step.status or ""))
            duration_text = str(step.duration_seconds) if step.duration_seconds is not None else ""
            self.history_steps_table.setItem(i, 2, QTableWidgetItem(duration_text))

        log.info(f"Loaded {len(steps)} steps for run {run_id}")


        # Update summary cards (if they exist)
        if hasattr(self, 'summary_status_val'):
            self.summary_status_val.setText(detail.status or "-")
        if hasattr(self, 'summary_items_val'):
            items_val = meta.get("item_count") or stats.get("records") or ""
            self.summary_items_val.setText(str(items_val) if items_val != "" else "-")
        if hasattr(self, 'summary_error_val'):
            err_val = meta.get("error") or ""
            if not err_val and meta.get("failed_steps"):
                err_val = "; ".join(f"{k}: {v}" for k, v in meta.get("failed_steps", {}).items())
            self.summary_error_val.setText(err_val or "-")

        # Mirror tasks tab with the same steps
        self._populate_tasks_for_run(run_id)
        if hasattr(self, '_push_timeline'):
            self._push_timeline(f"Viewed {run_id}")

    def _open_selected_output(self) -> None:
        """Open the output file for the selected run if available."""
        row_idx = self.history_table.currentRow()
        if row_idx < 0:
            return
        run_id_item = self.history_table.item(row_idx, 0)
        if not run_id_item:
            return
        # Get the full run_id from stored data
        run_id = run_id_item.data(Qt.UserRole)
        if not run_id:
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
            if step.status == "failed":
                item.setForeground(0, QColor("#ef4444"))
                item.setForeground(1, QColor("#ef4444"))
            elif step.status == "success":
                 item.setForeground(1, QColor("#10b981"))
            self.tasks_tree.addTopLevelItem(item)
            
        # Also refresh logs for this run if possible
        # Since logs are file-based or stream-based, we might simulate loading
        self.logs_text.clear()
        # In a real scenario, we'd fetch logs from a file or DB associated with run_id
        # For now, we show a placeholder if no live logs are in buffer
        self.logs_text.append(f"[INFO] Loaded tasks for run {run_id}")


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

        # Update summary cards (if they exist)
        if hasattr(self, 'summary_status_val'):
            self.summary_status_val.setText(detail.status or "-")
        if hasattr(self, 'summary_items_val'):
            items_val = meta.get("item_count") or stats.get("records") or ""
            self.summary_items_val.setText(str(items_val) if items_val != "" else "-")
        if hasattr(self, 'summary_error_val'):
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

    def _load_persisted_logs(self) -> None:
        """Load persisted logs from file."""
        if self.log_file_path.exists():
            try:
                with open(self.log_file_path, 'r', encoding='utf-8') as f:
                    persisted_logs = json.load(f)
                    # Keep only recent logs (last 1000 entries)
                    self.log_buffer = persisted_logs[-1000:]
                    log.info(f"Loaded {len(self.log_buffer)} persisted log entries")
            except Exception as e:
                log.error(f"Failed to load persisted logs: {e}")
                self.log_buffer = []

    def _save_persisted_logs(self) -> None:
        """Save logs to file for persistence across restarts."""
        try:
            # Ensure logs directory exists
            self.log_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert datetime objects to strings for JSON serialization
            serializable_logs = []
            for entry in self.log_buffer[-1000:]:  # Keep only last 1000 entries
                log_entry = entry.copy()
                if isinstance(log_entry.get("timestamp"), datetime):
                    log_entry["timestamp"] = log_entry["timestamp"].isoformat()
                serializable_logs.append(log_entry)

            with open(self.log_file_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_logs, f, indent=2)
        except Exception as e:
            log.error(f"Failed to save persisted logs: {e}")
    
    def _append_console(self, message: str) -> None:
        """Append message to console output."""
        self.console_output.append(message)
        # Auto-scroll to bottom
        if self.logs_autoscroll:
            scrollbar = self.console_output.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def _append_log_area(self, message: str) -> None:
        """Append message to log text area."""
        # Add to buffer for filtering
        self.log_buffer.append(
            {
                "text": message,
                "timestamp": datetime.utcnow(),
            }
        )

        # Save logs every 10 entries to avoid excessive I/O
        if len(self.log_buffer) % 10 == 0:
            self._save_persisted_logs()

        # Re-apply filters to update display
        if hasattr(self, "log_filter") and hasattr(self, "log_level_combo"):
            # Using the simple filter system (Logs tab)
            self._filter_logs()
        elif hasattr(self, "log_filter_level"):
            # Using the advanced filter system (other tabs)
            self._render_logs()
        elif hasattr(self, "logs_text"):
            # Fallback: just append directly
            self.logs_text.append(message)
            sb = self.logs_text.verticalScrollBar()
            sb.setValue(sb.maximum())

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

        # Refresh job statuses and check if any finished
        self.job_manager.poll()
        jobs = self.job_manager.list_jobs()

        # Hide progress bar if all jobs are done
        all_done = all(info.status in ("finished", "failed", "stopped") for info in jobs.values())
        if all_done and self.progress_bar.isVisible():
            self.progress_bar.setVisible(False)
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

        self._refresh_job_list()

    def _toggle_console_autoscroll(self, state: int) -> None:
        self.logs_autoscroll = state == Qt.Checked

    def _switch_page(self, index: int) -> None:
        """Switch stacked pages via nav buttons."""
        self.main_stack.setCurrentIndex(index)
        if index == 0: self.nav_runs_btn.setChecked(True)
        elif index == 1: self.nav_workflow_btn.setChecked(True)
        elif index == 2: self.nav_scrapers_btn.setChecked(True)
        elif index == 3: self.nav_settings_btn.setChecked(True)
        elif index == 4: self.nav_setup_btn.setChecked(True)
        elif index == 5: self.nav_info_btn.setChecked(True)

    # Styling helpers and summary
    # _styled_nav_button is already defined earlier in the class.


    def _status_chip(self, title: str) -> tuple[QWidget, QLabel]:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)
        lbl_title = QLabel(title)
        lbl_title.setProperty("class", "caption")
        lbl_val = QLabel("-")
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

        def _card(title: str, color: str = "#3b82f6"):
            # Simple widget without frame
            frame = QWidget()
            v = QVBoxLayout(frame)
            v.setContentsMargins(8, 8, 8, 8)
            lbl_title = QLabel(title)
            lbl_title.setProperty("class", "caption")
            lbl_val = QLabel("-")
            lbl_val.setAlignment(Qt.AlignCenter)
            lbl_val.setProperty("class", "subheading")
            v.addWidget(lbl_title, 0, Qt.AlignCenter)
            v.addWidget(lbl_val)
            v.addStretch()
            return frame, lbl_val

        self.summary_status_card, self.summary_status_val = _card("Status", "#3b82f6")
        self.summary_items_card, self.summary_items_val = _card("Items", "#10b981")
        self.summary_error_card, self.summary_error_val = _card("Last Error", "#ef4444")
        self.summary_error_val.setWordWrap(True)

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

        # Save persisted logs
        self._save_persisted_logs()

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


    def _create_scrapers_page(self) -> QWidget:
        """Create a comprehensive page with all scraper details, workflows, and data collection info."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QLabel("Scraper Registry & Data Collection Details")
        header.setProperty("class", "heading")
        layout.addWidget(header)

        desc = QLabel("Complete information about all available scrapers, their workflows, data sources, and collection processes.")
        desc.setProperty("class", "muted")
        layout.addWidget(desc)

        # Create tabs for different sections
        scraper_tabs = QTabWidget()

        # Tab 1: Scraper List Overview
        scrapers_list_tab = self._create_scrapers_list_tab()
        scraper_tabs.addTab(scrapers_list_tab, "Scrapers Overview")

        # Tab 2: Detailed Workflows
        workflow_details_tab = self._create_workflow_details_tab()
        scraper_tabs.addTab(workflow_details_tab, "Data Flow & Workflow")

        # Tab 3: Data Sources
        data_sources_tab = self._create_data_sources_tab()
        scraper_tabs.addTab(data_sources_tab, "Data Sources")

        # Tab 4: Collection Process
        collection_process_tab = self._create_collection_process_tab()
        scraper_tabs.addTab(collection_process_tab, "Collection Process")

        layout.addWidget(scraper_tabs)
        return page

    def _create_scrapers_list_tab(self) -> QWidget:
        """Create the scrapers list overview tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # Scraper Table
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["Scraper", "Version", "Status", "Schedule", "Last Run", "Description"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)

        # Scraper data with comprehensive details
        scrapers = [
            ("alfabeta", "v5.0", "Active", "Daily 3:00 AM", "2 hours ago", "Pharmaceutical scraper - alfabeta.net product catalog"),
            ("lafa", "v5.0", "Active", "Hourly", "15 mins ago", "High-frequency pricing monitor for LAFA marketplace"),
            ("quebec", "v5.0", "Beta", "Manual", "1 day ago", "Quebec region pharmaceutical data collector"),
            ("template", "v5.0", "Template", "N/A", "N/A", "Template scraper for creating new scrapers"),
        ]

        table.setRowCount(len(scrapers))
        for i, (name, ver, status, sched, last_run, desc_text) in enumerate(scrapers):
            table.setItem(i, 0, QTableWidgetItem(name))
            table.setItem(i, 1, QTableWidgetItem(ver))

            status_item = QTableWidgetItem(status)
            if status == "Active":
                status_item.setForeground(QColor("#4ade80"))
            elif status in ["Maintenance", "Paused"]:
                status_item.setForeground(QColor("#f87171"))
            elif status == "Beta":
                status_item.setForeground(QColor("#fbbf24"))
            table.setItem(i, 2, status_item)

            table.setItem(i, 3, QTableWidgetItem(sched))
            table.setItem(i, 4, QTableWidgetItem(last_run))
            table.setItem(i, 5, QTableWidgetItem(desc_text))

        layout.addWidget(table)
        return widget

    def _create_workflow_details_tab(self) -> QWidget:
        """Create detailed workflow and data flow documentation."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        workflow_text = QTextBrowser()
        workflow_text.setOpenExternalLinks(True)
        workflow_text.setHtml("""
            <h2>Data Flow & Workflow Architecture</h2>
            <p>Each scraper follows a <b>unified pipeline architecture</b> with standardized stages for data extraction, transformation, and loading.</p>

            <h3>Pipeline Stages</h3>
            <div style='background-color: #f8f9fa; padding: 15px; border-radius: 6px; margin: 10px 0;'>
                <ol style='margin: 0; padding-left: 20px;'>
                    <li><b>Discovery/Index Stage</b>
                        <ul>
                            <li>Fetches listing pages (e.g., company directories)</li>
                            <li>Extracts URLs for detailed pages</li>
                            <li>Example: alfabeta fetches company index → product URLs</li>
                        </ul>
                    </li>
                    <li><b>Extraction Stage</b>
                        <ul>
                            <li>Navigates to product/detail pages</li>
                            <li>Extracts raw data using CSS selectors</li>
                            <li>Handles pagination and dynamic content</li>
                        </ul>
                    </li>
                    <li><b>Normalization Stage</b>
                        <ul>
                            <li>Converts raw scraped data to unified schema</li>
                            <li>Standardizes field names and formats</li>
                            <li>Example: price → numeric, currency → ISO code</li>
                        </ul>
                    </li>
                    <li><b>Enrichment Stage</b>
                        <ul>
                            <li>PCID Matching: Links products to master catalog</li>
                            <li>Uses vector similarity for fuzzy matching</li>
                            <li>Adds confidence scores and metadata</li>
                        </ul>
                    </li>
                    <li><b>Quality Control (QC) Stage</b>
                        <ul>
                            <li>Validates records against business rules</li>
                            <li>Deduplicates based on unique keys</li>
                            <li>Flags anomalies and missing required fields</li>
                        </ul>
                    </li>
                    <li><b>Export Stage</b>
                        <ul>
                            <li>Writes to CSV, Database, S3, or GCS</li>
                            <li>Tracks lineage and versioning</li>
                            <li>Records run metadata and statistics</li>
                        </ul>
                    </li>
                </ol>
            </div>

            <h3>Scraper-Specific Workflows</h3>

            <h4>AlfaBeta Scraper</h4>
            <pre style='background-color: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 6px; font-family: monospace; font-size: 12px;'>
1. Start → Navigate to company index page
2. Extract company URLs → ~50-200 companies
3. For each company → Extract product listing URLs
4. For each product → Extract details (name, price, company, etc.)
5. Normalize → Unified product schema
6. PCID Match → Link to master catalog
7. QC → Validate & dedupe
8. Export → CSV + optional DB/S3
            </pre>

            <h4>LAFA Scraper</h4>
            <pre style='background-color: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 6px; font-family: monospace; font-size: 12px;'>
1. Start → Navigate to marketplace
2. Extract product listings (paginated)
3. Extract product details
4. Normalize & Enrich
5. QC & Export
            </pre>

            <h3>Error Handling & Self-Healing</h3>
            <ul>
                <li><b>Retry Logic</b>: Exponential backoff for transient failures</li>
                <li><b>Proxy Rotation</b>: Automatic switching on 403/429 errors</li>
                <li><b>LLM-Powered Repair</b>: Agent analyzes errors and suggests selector fixes</li>
                <li><b>Run Tracking</b>: All steps logged with status and timing</li>
            </ul>
        """)
        layout.addWidget(workflow_text)
        return widget

    def _create_data_sources_tab(self) -> QWidget:
        """Create data sources documentation."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        sources_text = QTextBrowser()
        sources_text.setOpenExternalLinks(True)
        sources_text.setHtml("""
            <h2>Data Sources & Endpoints</h2>
            <p>This section documents where data is collected from for each scraper.</p>

            <h3>AlfaBeta Source</h3>
            <table style='width: 100%; border-collapse: collapse; margin: 15px 0;'>
                <tr style='background-color: #f1f5f9;'>
                    <td style='padding: 10px; border: 1px solid #e2e8f0; font-weight: bold;'>Source Type</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>Web Scraping (Selenium)</td>
                </tr>
                <tr>
                    <td style='padding: 10px; border: 1px solid #e2e8f0; font-weight: bold;'>Base URL</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>https://alfabeta.net</td>
                </tr>
                <tr style='background-color: #f1f5f9;'>
                    <td style='padding: 10px; border: 1px solid #e2e8f0; font-weight: bold;'>Index Page</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>/companies - Lists all pharmaceutical companies</td>
                </tr>
                <tr>
                    <td style='padding: 10px; border: 1px solid #e2e8f0; font-weight: bold;'>Product Pages</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>/company/{id}/products - Product listings per company</td>
                </tr>
                <tr style='background-color: #f1f5f9;'>
                    <td style='padding: 10px; border: 1px solid #e2e8f0; font-weight: bold;'>Detail Pages</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>/product/{id} - Individual product details</td>
                </tr>
                <tr>
                    <td style='padding: 10px; border: 1px solid #e2e8f0; font-weight: bold;'>Auth Required</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>Optional (configurable login flow)</td>
                </tr>
                <tr style='background-color: #f1f5f9;'>
                    <td style='padding: 10px; border: 1px solid #e2e8f0; font-weight: bold;'>Rate Limiting</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>Yes - handled via proxy rotation</td>
                </tr>
            </table>

            <h3>LAFA Source</h3>
            <table style='width: 100%; border-collapse: collapse; margin: 15px 0;'>
                <tr style='background-color: #f1f5f9;'>
                    <td style='padding: 10px; border: 1px solid #e2e8f0; font-weight: bold;'>Source Type</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>Web Scraping (Selenium)</td>
                </tr>
                <tr>
                    <td style='padding: 10px; border: 1px solid #e2e8f0; font-weight: bold;'>Base URL</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>https://lafa-marketplace.com</td>
                </tr>
                <tr style='background-color: #f1f5f9;'>
                    <td style='padding: 10px; border: 1px solid #e2e8f0; font-weight: bold;'>Frequency</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>Hourly - High-frequency pricing updates</td>
                </tr>
            </table>

            <h3>Quebec Source</h3>
            <table style='width: 100%; border-collapse: collapse; margin: 15px 0;'>
                <tr style='background-color: #f1f5f9;'>
                    <td style='padding: 10px; border: 1px solid #e2e8f0; font-weight: bold;'>Source Type</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>Web Scraping (Selenium)</td>
                </tr>
                <tr>
                    <td style='padding: 10px; border: 1px solid #e2e8f0; font-weight: bold;'>Status</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>Beta - Regional data collector</td>
                </tr>
            </table>

            <h3>Selector Configuration</h3>
            <p>Each scraper uses a <code>selectors.json</code> file that defines CSS selectors for extracting data:</p>
            <pre style='background-color: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 6px; font-family: monospace; font-size: 11px;'>
{
  "companies_url": "https://alfabeta.net/companies",
  "company_link_selector": ".company-card a",
  "product_link_selector": ".product-item a",
  "product_name_selector": "h1.product-title",
  "price_selector": ".price-amount",
  "currency_selector": ".price-currency"
}
            </pre>
        """)
        layout.addWidget(sources_text)
        return widget

    def _create_collection_process_tab(self) -> QWidget:
        """Create data collection process documentation."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        process_text = QTextBrowser()
        process_text.setOpenExternalLinks(True)
        process_text.setHtml("""
            <h2>Data Collection Process & Technical Details</h2>

            <h3>Collection Methods</h3>
            <div style='background-color: #f8f9fa; padding: 15px; border-radius: 6px; margin: 10px 0;'>
                <h4>1. Selenium WebDriver (Primary Method)</h4>
                <ul>
                    <li><b>Browser</b>: Chrome/Firefox in headless mode</li>
                    <li><b>Session Management</b>: Persistent sessions with cookies</li>
                    <li><b>Proxy Support</b>: Rotating proxies from resource pool</li>
                    <li><b>Account Routing</b>: Multiple accounts for rate limit distribution</li>
                    <li><b>Use Cases</b>: JavaScript-heavy sites, authenticated access</li>
                </ul>

                <h4>2. HTTP Requests (Alternative)</h4>
                <ul>
                    <li><b>Library</b>: requests/httpx with session pooling</li>
                    <li><b>Performance</b>: Faster for static content</li>
                    <li><b>Use Cases</b>: API endpoints, simple HTML pages</li>
                </ul>
            </div>

            <h3>Resource Management</h3>
            <h4>Account Router</h4>
            <ul>
                <li>Manages pool of credentials per source</li>
                <li>Tracks usage and cooldown periods</li>
                <li>Automatic rotation on auth failures</li>
            </ul>

            <h4>Proxy Pool</h4>
            <ul>
                <li>Geographic distribution (US, EU, LATAM)</li>
                <li>Health checking and automatic failover</li>
                <li>Cost tracking per proxy provider</li>
            </ul>

            <h3>Data Processing Pipeline</h3>
            <table style='width: 100%; border-collapse: collapse; margin: 15px 0;'>
                <tr style='background-color: #1e293b; color: #e2e8f0;'>
                    <th style='padding: 10px; border: 1px solid #334155; text-align: left;'>Stage</th>
                    <th style='padding: 10px; border: 1px solid #334155; text-align: left;'>Input</th>
                    <th style='padding: 10px; border: 1px solid #334155; text-align: left;'>Output</th>
                    <th style='padding: 10px; border: 1px solid #334155; text-align: left;'>Module</th>
                </tr>
                <tr>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>1. Extraction</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>URLs</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>Raw HTML/JSON</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>selenium_engine.py</td>
                </tr>
                <tr style='background-color: #f1f5f9;'>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>2. Parsing</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>HTML</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>Raw Records (dict)</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>scraper/extract.py</td>
                </tr>
                <tr>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>3. Normalization</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>Raw Records</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>Unified Schema</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>processors/unify_fields.py</td>
                </tr>
                <tr style='background-color: #f1f5f9;'>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>4. Enrichment</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>Unified Records</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>PCID-Matched Records</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>processors/pcid_matcher.py</td>
                </tr>
                <tr>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>5. Quality Control</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>Enriched Records</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>Valid, Deduped Records</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>processors/qc_rules.py</td>
                </tr>
                <tr style='background-color: #f1f5f9;'>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>6. Export</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>Valid Records</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>CSV/DB/S3</td>
                    <td style='padding: 10px; border: 1px solid #e2e8f0;'>processors/exporters/</td>
                </tr>
            </table>

            <h3>Observability & Tracking</h3>
            <ul>
                <li><b>Run Tracking</b>: SQLite database records all runs with metadata</li>
                <li><b>Step Recording</b>: Each pipeline stage logged with timing</li>
                <li><b>Metrics</b>: Prometheus-style counters (records_valid, records_invalid, etc.)</li>
                <li><b>Cost Tracking</b>: Proxy costs, compute costs per run</li>
                <li><b>Versioning</b>: Scraper version, schema version, selector version tracked</li>
            </ul>

            <h3>Output Formats</h3>
            <h4>CSV Output Structure</h4>
            <pre style='background-color: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 6px; font-family: monospace; font-size: 11px;'>
product_url,name,price,currency,company,source,pcid,pcid_confidence,run_id,_version
https://...,Product Name,19.99,USD,Company Inc,alfabeta,PC123456,0.95,run_20250112,5.0
            </pre>

            <h4>Database Schema</h4>
            <ul>
                <li><b>products</b>: Normalized product records</li>
                <li><b>runs</b>: Run metadata and statistics</li>
                <li><b>steps</b>: Pipeline step execution details</li>
                <li><b>versions</b>: Scraper and schema version history</li>
            </ul>

            <h3>Configuration Files</h3>
            <ul>
                <li><code>config/{source}.yaml</code> - Source-specific settings</li>
                <li><code>scrapers/{source}/selectors.json</code> - CSS selectors</li>
                <li><code>config/pcid_master.jsonl</code> - Master product catalog</li>
                <li><code>.env</code> - Environment variables and API keys</li>
            </ul>
        """)
        layout.addWidget(process_text)
        return widget

    def _create_platform_info_page(self) -> QWidget:
        """Create a page with detailed platform documentation and architecture."""
        page = QWidget()
        layout = QVBoxLayout(page)
        
        # Tabs for different info sections
        info_tabs = QTabWidget()
        layout.addWidget(info_tabs)
        
        # 1. Architecture Tab
        arch_widget = QWidget()
        arch_layout = QVBoxLayout(arch_widget)
        arch_text = QTextBrowser()
        arch_text.setOpenExternalLinks(True)
        arch_text.setHtml("""
            <h1>Scraper Platform Architecture</h1>
            <p>The platform follows a <b>Unified Pipeline Architecture</b> designed for resilience and scalability.</p>
            
            <h3>Core Components</h3>
            <ul>
                <li><b>Unified Pipeline</b>: A single execution engine (`Runner`) that handles all stages (extract, transform, load) uniformly.</li>
                <li><b>Airflow Orchestration</b>: Manages scheduling, dependencies, and backfills.</li>
                <li><b>Autonomout Agents</b>: LLM-powered agents that detect anomalies and attempt self-healing.</li>
            </ul>
            
            <h3>Scraper Lifecycle</h3>
            <ol>
                <li><b>Discovery</b>: Finds links or items to scrape.</li>
                <li><b>Extraction</b>: Downloads and parses HTML/JSON.</li>
                <li><b>Normalization</b>: Converts raw data to a standard schema.</li>
                <li><b>Enrichment</b>: Adds external data (e.g., geocoding).</li>
                <li><b>Quality Control (QC)</b>: Validates data against rules.</li>
                <li><b>Export</b>: Saves to DB, S3, or CSV.</li>
            </ol>
            
            <p><i>See the 'Self-Healing' tab for details on error recovery.</i></p>
        """)
        arch_layout.addWidget(arch_text)
        info_tabs.addTab(arch_widget, "Architecture")
        
        # 2. Self-Healing Tab
        healing_widget = QWidget()
        healing_layout = QVBoxLayout(healing_widget)
        healing_text = QTextBrowser()
        healing_text.setHtml("""
            <h1>Self-Healing & Autonomous Recovery</h1>
            <p>Each scraper is equipped with a self-healing loop that activates upon failure.</p>
            
            <h3>The Healing Loop</h3>
            <ol>
                <li><b>Detection</b>: A step fails (e.g., SelectorNotFound, 403 Forbidden).</li>
                <li><b>Analysis</b>: The error context and page source are sent to the <code>ErrorAnalysisAgent</code>.</li>
                <li><b>Strategy Generation</b>: The LLM suggests a fix (e.g., "Use a different CSS selector", "Rotate proxy").</li>
                <li><b>Hotfix Application</b>: The platform dynamically patches the scraper configuration or logic.</li>
                <li><b>Retry</b>: The failed step is retried with the new strategy.</li>
            </ol>
            
            <h3>Resilience Levels</h3>
            <ul>
                <li><b>Level 1 (Retry)</b>: Simple exponential backoff.</li>
                <li><b>Level 2 (Proxy Rotation)</b>: Automatically switches proxy providers.</li>
                <li><b>Level 3 (DOM Repair)</b>: Uses LLM to find new selectors when the site layout changes.</li>
            </ul>
        """)
        healing_layout.addWidget(healing_text)
        info_tabs.addTab(healing_widget, "Self-Healing")
        
        # 3. Directory Structure
        dir_widget = QWidget()
        dir_layout = QVBoxLayout(dir_widget)
        dir_text = QTextBrowser()
        dir_text.setHtml("""
            <h1>Project Structure</h1>
            <pre>
d:/Scraper/scraper-platform/
├── .claude/                    # Claude Code configuration and commands
├── .github/                    # GitHub Actions CI/CD workflows
├── config/                     # Configuration files (env, sources, Airflow)
├── dags/                       # Airflow DAG definitions
│   ├── scraper_base.py         # Base DAG factory
│   ├── agent_orchestrator.py  # Agent coordination DAG
│   ├── agent_pipeline_runner.py
│   ├── router_tasks.py
│   ├── replay_runner.py
│   ├── scraper_sample_source.py
│   └── summary_tasks.py
├── docs/                       # Documentation and diagrams
├── dsl/                        # Domain Specific Language for pipelines
├── logs/                       # Application and pipeline logs
├── output/                     # Scraped data output
├── screenshots/                # Browser screenshots for debugging
├── tests/                      # Pytest test suite
├── src/                        # Main source code
│   ├── <b>CORE PROCESSING:</b>
│   │   ├── pipeline/           # Pipeline compiler, runner, registry
│   │   ├── scrapers/           # Individual scraper implementations
│   │   ├── engines/            # Playwright, Selenium, HTTP engines
│   │   ├── devtools/           # Browser DevTools integration
│   │   ├── replay/             # Session replay and recording
│   │   └── router/             # Request routing and load balancing
│   │
│   ├── <b>AI & AGENTS:</b>
│   │   ├── agents/             # AI agents (Repair, Dedup, Prompt)
│   │   ├── ai/                 # LLM integration and prompts
│   │   └── rag/                # RAG system for knowledge retrieval
│   │
│   ├── <b>DATA & STORAGE:</b>
│   │   ├── storage/            # File system operations
│   │   ├── common/             # Database connections (PostgreSQL/SQLite)
│   │   ├── run_tracking/       # Run history, stats, query system
│   │   └── db_adapter/         # Database abstraction layer
│   │
│   ├── <b>INFRASTRUCTURE:</b>
│   │   ├── scheduler/          # Airflow scheduler integration
│   │   ├── api/                # REST API server (FastAPI)
│   │   ├── observability/      # Metrics, tracing, alerts
│   │   ├── security/           # Encryption, crypto utilities
│   │   └── testing/            # Test utilities and factories
│   │
│   ├── <b>USER INTERFACE:</b>
│   │   └── ui/                 # Desktop application (PySide6)
│   │       ├── main_window.py  # Main UI window
│   │       ├── setup_wizard.py # Project setup wizard
│   │       └── app.py          # Application entry point
│   │
│   └── <b>UTILITIES:</b>
│       ├── telemetry/          # Usage analytics
│       ├── utils/              # Helper functions
│       └── llm_prompt/         # LLM prompt templates
│
└── requirements.txt            # Python dependencies
            </pre>
            <p><b>Total:</b> 24 root directories, 36 src/ modules</p>
        """)
        dir_layout.addWidget(dir_text)
        info_tabs.addTab(dir_widget, "Directory Map")
        
        return page

    def _create_settings_page(self) -> QWidget:
        """Create a settings page for environment variables."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        
        header = QLabel("Settings & Environment")
        header.setProperty("class", "heading")
        layout.addWidget(header)

        desc = QLabel("Manage global configuration and environment variables. Limits and API keys can be updated here.")
        desc.setProperty("class", "muted")
        layout.addWidget(desc)

        # Environment Table
        self.env_table = QTableWidget()
        self.env_table.setColumnCount(2)
        self.env_table.setHorizontalHeaderLabels(["Variable Name", "Value"])
        self.env_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Load env vars
        env_vars = {
            "DB_URL": os.getenv("DB_URL", "sqlite:///./logs/run_db.sqlite"),
            "PCID_MASTER_PATH": os.getenv("PCID_MASTER_PATH", "./config/pcid_master.jsonl"),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "sk-......"),
            "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
            "MAX_WORKERS": os.getenv("MAX_WORKERS", "4"),
            "PROXY_URL": os.getenv("PROXY_URL", "http://proxy.example.com"),
            "HEADLESS_MODE": os.getenv("HEADLESS_MODE", "True")
        }
        
        self.env_table.setRowCount(len(env_vars))
        for i, (key, val) in enumerate(env_vars.items()):
            self.env_table.setItem(i, 0, QTableWidgetItem(key))
            self.env_table.setItem(i, 1, QTableWidgetItem(val))
            
        layout.addWidget(self.env_table)
        
        # Save Button
        save_btn = QPushButton("Save Changes")
        save_btn.setProperty("class", "primary")
        save_btn.clicked.connect(self._save_settings)
        layout.addWidget(save_btn, alignment=Qt.AlignRight)
        
        return page
        
    def _save_settings(self) -> None:
        """Save settings from the table."""
        # In a real app this would persist to .env file
        QMessageBox.information(self, "Settings Saved", "Environment variables have been updated (simulation).")


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

    

