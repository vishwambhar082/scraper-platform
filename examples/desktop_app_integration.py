"""
Complete desktop application integration example.

Demonstrates:
- Execution engine integration
- Scheduler setup
- UI with all components
- Security (PIN lock)
- Health dashboard
- Run comparison
- Diagnostics export
"""

import sys
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget
from PySide6.QtCore import QTimer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def create_desktop_app():
    """Create complete desktop application."""
    from ui.components import (
        HealthDashboard,
        RunHistoryWidget,
        RunComparisonWidget
    )
    from ui.security import AuthManager, LockScreen, AuditViewer
    from observability import DiagnosticsExporter
    from execution import CoreExecutionEngine
    from scheduler import DesktopScheduler

    # Paths
    base_dir = Path.cwd() / 'scraper_data'
    base_dir.mkdir(exist_ok=True)

    config_dir = base_dir / 'config'
    config_dir.mkdir(exist_ok=True)

    logs_dir = base_dir / 'logs'
    logs_dir.mkdir(exist_ok=True)

    db_dir = base_dir / 'db'
    db_dir.mkdir(exist_ok=True)

    output_dir = base_dir / 'output'
    output_dir.mkdir(exist_ok=True)

    # Create main window
    class DesktopApp(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Scraper Platform - Desktop Edition")
            self.setMinimumSize(1200, 800)

            # Core components
            self.execution_engine = CoreExecutionEngine()
            self.scheduler = DesktopScheduler(
                db_path=db_dir / 'scheduler.db',
                execution_engine=self.execution_engine
            )

            # Security
            self.auth_manager = AuthManager(config_dir)
            self.lock_screen = None
            self.idle_timer = None

            # Diagnostics
            self.diagnostics_exporter = DiagnosticsExporter(
                output_dir=output_dir / 'diagnostics',
                logs_dir=logs_dir,
                config_dir=config_dir,
                db_dir=db_dir
            )

            self._init_ui()
            self._setup_security()
            self._start_background_tasks()

        def _init_ui(self):
            """Initialize UI components."""
            # Tab widget
            tabs = QTabWidget()
            self.setCentralWidget(tabs)

            # 1. Health Dashboard
            self.health_dashboard = HealthDashboard()
            self.health_dashboard.export_diagnostics_requested.connect(
                self._on_export_diagnostics
            )
            tabs.addTab(self.health_dashboard, "Health Dashboard")

            # 2. Run History
            self.run_history = RunHistoryWidget()
            self.run_history.comparison_requested.connect(
                self._on_comparison_requested
            )
            tabs.addTab(self.run_history, "Run History")

            # 3. Run Comparison
            self.run_comparison = RunComparisonWidget()
            self.run_comparison.comparison_requested.connect(
                self._load_comparison_data
            )
            tabs.addTab(self.run_comparison, "Run Comparison")

            # 4. Security Audit
            self.audit_viewer = AuditViewer(
                audit_file=config_dir / 'security_audit.log'
            )
            tabs.addTab(self.audit_viewer, "Security Audit")

            # Update UI with initial data
            self._update_health_dashboard()

        def _setup_security(self):
            """Setup security features."""
            # Check if PIN required on start
            if self.auth_manager.has_pin() and self.auth_manager.is_pin_required_on_start():
                self._show_lock_screen()

            # Setup auto-lock
            if self.auth_manager.is_auto_lock_enabled():
                from ui.security import IdleMonitor

                self.idle_monitor = IdleMonitor(
                    timeout_minutes=self.auth_manager.get_auto_lock_minutes()
                )

                # Check idle every 30 seconds
                self.idle_timer = QTimer()
                self.idle_timer.timeout.connect(self._check_idle)
                self.idle_timer.start(30000)

        def _show_lock_screen(self):
            """Show lock screen."""
            if not self.lock_screen:
                self.lock_screen = LockScreen(self.auth_manager, self)
                self.lock_screen.authenticated.connect(self._on_authenticated)

            result = self.lock_screen.exec()
            if result != self.lock_screen.Accepted:
                # User failed authentication
                logger.warning("Authentication failed, closing application")
                self.close()

        def _on_authenticated(self):
            """Handle successful authentication."""
            logger.info("User authenticated")
            if hasattr(self, 'idle_monitor'):
                self.idle_monitor.reset()

        def _check_idle(self):
            """Check if user is idle."""
            if hasattr(self, 'idle_monitor') and self.idle_monitor.is_idle():
                logger.info("User idle, locking application")
                self.auth_manager.log_security_event('auto_lock_triggered', {
                    'idle_minutes': self.idle_monitor.get_idle_minutes()
                })
                self._show_lock_screen()

        def _start_background_tasks(self):
            """Start background tasks."""
            # Start scheduler
            self.scheduler.start()
            logger.info("Scheduler started")

            # Update health dashboard every 5 seconds
            self.health_timer = QTimer()
            self.health_timer.timeout.connect(self._update_health_dashboard)
            self.health_timer.start(5000)

            # Update run history every 30 seconds
            self.history_timer = QTimer()
            self.history_timer.timeout.connect(self._update_run_history)
            self.history_timer.start(30000)

            # Initial update
            self._update_run_history()

        def _update_health_dashboard(self):
            """Update health dashboard with latest stats."""
            # Get engine stats
            engine_stats = self.execution_engine.get_stats()
            self.health_dashboard.update_engine_status(engine_stats)

            # Get scheduler stats
            scheduler_stats = self.scheduler.get_stats()
            self.health_dashboard.update_scheduler_status(scheduler_stats)

        def _update_run_history(self):
            """Update run history."""
            # Get recent executions
            active = self.execution_engine.list_active_executions()

            # Convert to display format
            runs = []
            for ctx in active:
                runs.append({
                    'run_id': ctx.run_id,
                    'pipeline_id': ctx.pipeline_id,
                    'source': ctx.source,
                    'state': ctx.state.value,
                    'started_at': ctx.started_at.isoformat() if ctx.started_at else '',
                    'duration_seconds': (ctx.finished_at - ctx.started_at).total_seconds()
                        if ctx.finished_at and ctx.started_at else 0,
                    'progress': ctx.progress
                })

            self.run_history.set_runs(runs)
            self.run_comparison.set_available_runs(runs)

        def _on_comparison_requested(self, run_id1: str, run_id2: str):
            """Handle comparison request from history."""
            # Switch to comparison tab
            tabs = self.centralWidget()
            tabs.setCurrentIndex(2)  # Comparison tab

            # Load comparison
            self._load_comparison_data(run_id1, run_id2)

        def _load_comparison_data(self, run_id1: str, run_id2: str):
            """Load data for comparison."""
            # Get execution contexts
            ctx1 = self.execution_engine.get_execution_state(run_id1)
            ctx2 = self.execution_engine.get_execution_state(run_id2)

            if not ctx1 or not ctx2:
                logger.error(f"Failed to load comparison data for {run_id1} and {run_id2}")
                return

            # Convert to dicts
            run1_data = {
                'run_id': ctx1.run_id,
                'pipeline_id': ctx1.pipeline_id,
                'source': ctx1.source,
                'state': ctx1.state.value,
                'started_at': ctx1.started_at.isoformat() if ctx1.started_at else '',
                'finished_at': ctx1.finished_at.isoformat() if ctx1.finished_at else '',
                'duration_seconds': (ctx1.finished_at - ctx1.started_at).total_seconds()
                    if ctx1.finished_at and ctx1.started_at else 0,
                'progress': ctx1.progress,
                'completed_steps': ctx1.completed_steps,
                'total_steps': ctx1.total_steps,
                'completed_step_ids': ctx1.completed_step_ids,
                'error': ctx1.error
            }

            run2_data = {
                'run_id': ctx2.run_id,
                'pipeline_id': ctx2.pipeline_id,
                'source': ctx2.source,
                'state': ctx2.state.value,
                'started_at': ctx2.started_at.isoformat() if ctx2.started_at else '',
                'finished_at': ctx2.finished_at.isoformat() if ctx2.finished_at else '',
                'duration_seconds': (ctx2.finished_at - ctx2.started_at).total_seconds()
                    if ctx2.finished_at and ctx2.started_at else 0,
                'progress': ctx2.progress,
                'completed_steps': ctx2.completed_steps,
                'total_steps': ctx2.total_steps,
                'completed_step_ids': ctx2.completed_step_ids,
                'error': ctx2.error
            }

            self.run_comparison.set_comparison_data(run1_data, run2_data)

        def _on_export_diagnostics(self):
            """Export diagnostics bundle."""
            logger.info("Exporting diagnostics bundle...")

            try:
                # Get current stats
                engine_stats = self.execution_engine.get_stats()
                scheduler_stats = self.scheduler.get_stats()

                # Get recent errors from health dashboard
                recent_errors = []
                errors_text = self.health_dashboard.errors_text.toPlainText()
                if errors_text:
                    recent_errors = errors_text.split('\n')[:20]

                # Export
                bundle_path = self.diagnostics_exporter.export_bundle(
                    execution_engine_stats=engine_stats,
                    scheduler_stats=scheduler_stats,
                    recent_errors=recent_errors
                )

                logger.info(f"Diagnostics exported to: {bundle_path}")

                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self,
                    "Diagnostics Exported",
                    f"Diagnostics bundle exported to:\n{bundle_path}"
                )

            except Exception as e:
                logger.error(f"Failed to export diagnostics: {e}", exc_info=True)

                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"Failed to export diagnostics:\n{str(e)}"
                )

        def closeEvent(self, event):
            """Handle window close."""
            logger.info("Shutting down application...")

            # Stop scheduler
            self.scheduler.stop()

            # Shutdown execution engine
            self.execution_engine.shutdown()

            logger.info("Application shutdown complete")
            event.accept()

    return DesktopApp


def main():
    """Run desktop application."""
    app = QApplication(sys.argv)

    # Create and show window
    window_class = create_desktop_app()
    window = window_class()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
