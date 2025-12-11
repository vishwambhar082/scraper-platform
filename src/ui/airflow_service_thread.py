"""
Thread for starting Airflow services without blocking the UI.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from src.ui.airflow_service import AirflowServiceManager
from src.common.logging_utils import get_logger

log = get_logger("airflow-service-thread")


class AirflowServiceStartThread(QThread):
    """Thread for starting Airflow services."""
    
    started = Signal(bool, str)  # success, message
    status_update = Signal(str)  # status message
    
    def __init__(self, service_manager: AirflowServiceManager):
        super().__init__()
        self.service_manager = service_manager
    
    def run(self) -> None:
        """Start Airflow services."""
        try:
            self.status_update.emit("Initializing database...")
            if not self.service_manager.initialize_airflow_db():
                self.started.emit(False, "Failed to initialize Airflow database")
                return
            
            self.status_update.emit("Starting scheduler...")
            if not self.service_manager.start_scheduler():
                self.started.emit(False, "Failed to start scheduler")
                return
            
            self.status_update.emit("Starting API server...")
            if not self.service_manager.start_api_server():
                self.service_manager.stop_scheduler()
                self.started.emit(False, "API server failed to start. Check auth manager configuration.")
                return
            
            self.status_update.emit("Waiting for API to be ready...")
            if self.service_manager.wait_for_api_ready(timeout=30):
                self.started.emit(True, "All services started successfully")
            else:
                self.started.emit(False, "Services started but API not responding. Check logs.")
        except Exception as e:
            log.error(f"Error starting services: {e}", exc_info=True)
            self.started.emit(False, f"Error: {str(e)}")

