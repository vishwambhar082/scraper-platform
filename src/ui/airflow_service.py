"""
Airflow service manager for desktop application.

Manages Airflow processes (scheduler, API server) and provides
start/stop functionality for the desktop UI.

Note: Airflow has limited Windows support. For best results, use WSL2 or Linux.
On Windows, some features may not work perfectly, but basic functionality should work.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Optional, List, Dict
import os

from src.common.logging_utils import get_logger

log = get_logger("airflow-service")


class AirflowServiceManager:
    """Manages Airflow backend services (scheduler, API server)."""
    
    def __init__(self, airflow_home: Optional[Path] = None) -> None:
        """Initialize the Airflow service manager.
        
        Args:
            airflow_home: Path to Airflow home directory (defaults to ~/airflow)
        """
        self.airflow_home = airflow_home or Path.home() / "airflow"
        self.scheduler_process: Optional[subprocess.Popen] = None
        self.api_server_process: Optional[subprocess.Popen] = None
        self.api_port = 8080
        
        # Determine how to run airflow (command vs python -m)
        self._airflow_cmd = self._get_airflow_command()
        
    def _get_airflow_command(self) -> List[str]:
        """Get the command to run Airflow.
        
        Returns:
            List of command parts (e.g., ['python', '-m', 'airflow'] or ['airflow'])
        """
        # Try importing airflow first (most reliable)
        try:
            import airflow
            # Use python -m airflow (works even if airflow command not in PATH)
            import sys
            return [sys.executable, "-m", "airflow"]
        except ImportError:
            pass
        
        # Fallback: try airflow command
        try:
            result = subprocess.run(
                ["airflow", "version"],
                capture_output=True,
                timeout=2,
            )
            if result.returncode == 0:
                return ["airflow"]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Default fallback
        import sys
        return [sys.executable, "-m", "airflow"]
    
    def is_airflow_installed(self) -> bool:
        """Check if Airflow is installed."""
        # Try importing airflow (most reliable method)
        try:
            import airflow
            return True
        except ImportError:
            pass
        
        # Fallback: try running airflow command
        try:
            result = subprocess.run(
                self._airflow_cmd + ["version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def initialize_airflow_db(self) -> bool:
        """Initialize Airflow database if needed.
        
        Returns:
            True if initialization successful or already exists
        """
        # Check if database exists (SQLite or check for config file)
        db_exists = (
            (self.airflow_home / "airflow.db").exists() or
            (self.airflow_home / "airflow.cfg").exists()
        )
        
        if db_exists:
            log.info("Airflow database/config already exists")
            return True
        
        try:
            # Create airflow home directory if it doesn't exist
            self.airflow_home.mkdir(parents=True, exist_ok=True)
            
            # Airflow 3.x will auto-initialize database on first run
            # We don't need to run 'db init' or 'db migrate' manually
            # The scheduler/api-server will handle initialization
            log.info("Airflow home directory ready. Database will initialize on first service start.")
            return True
        except Exception as e:
            log.error(f"Error initializing Airflow database: {e}")
            return False
    
    def start_scheduler(self) -> bool:
        """Start Airflow scheduler.
        
        Returns:
            True if started successfully
        """
        if self.scheduler_process and self.scheduler_process.poll() is None:
            log.info("Scheduler already running")
            return True
        
        try:
            log.info("Starting Airflow scheduler...")
            env = os.environ.copy()
            env["AIRFLOW_HOME"] = str(self.airflow_home)
            
            self.scheduler_process = subprocess.Popen(
                self._airflow_cmd + ["scheduler"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )
            
            # Wait a bit to see if it starts successfully
            time.sleep(2)
            if self.scheduler_process.poll() is not None:
                log.error("Scheduler process exited immediately")
                return False
            
            log.info("Airflow scheduler started successfully")
            return True
        except Exception as e:
            log.error(f"Failed to start scheduler: {e}")
            return False
    
    def start_api_server(self) -> bool:
        """Start Airflow API server.
        
        Returns:
            True if started successfully
        """
        if self.api_server_process and self.api_server_process.poll() is None:
            log.info("API server already running")
            return True
        
        try:
            log.info(f"Starting Airflow API server on port {self.api_port}...")
            env = os.environ.copy()
            env["AIRFLOW_HOME"] = str(self.airflow_home)
            
            # Capture stderr to check for errors
            self.api_server_process = subprocess.Popen(
                self._airflow_cmd + ["api-server", "--port", str(self.api_port)],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                text=True,
            )
            
            # Wait a bit and check if process is still running
            time.sleep(2)
            if self.api_server_process.poll() is not None:
                # Process exited - get error message
                try:
                    _, stderr = self.api_server_process.communicate(timeout=1)
                    error_msg = stderr[:500] if stderr else "Unknown error"
                except subprocess.TimeoutExpired:
                    error_msg = "Process exited before we could read error"
                
                log.error(f"API server process exited immediately: {error_msg}")
                
                # Check for common issues
                if "auth_manager" in error_msg.lower() or "auth" in error_msg.lower():
                    log.error("Auth manager configuration issue detected - API server requires auth manager setup")
                return False
            
            log.info("Airflow API server started successfully")
            return True
        except Exception as e:
            log.error(f"Failed to start API server: {e}", exc_info=True)
            return False
    
    def stop_scheduler(self) -> None:
        """Stop Airflow scheduler."""
        if self.scheduler_process:
            try:
                self.scheduler_process.terminate()
                self.scheduler_process.wait(timeout=5)
                log.info("Scheduler stopped")
            except subprocess.TimeoutExpired:
                self.scheduler_process.kill()
                log.warning("Scheduler force-killed")
            except Exception as e:
                log.error(f"Error stopping scheduler: {e}")
            finally:
                self.scheduler_process = None
    
    def stop_api_server(self) -> None:
        """Stop Airflow API server."""
        if self.api_server_process:
            try:
                self.api_server_process.terminate()
                self.api_server_process.wait(timeout=5)
                log.info("API server stopped")
            except subprocess.TimeoutExpired:
                self.api_server_process.kill()
                log.warning("API server force-killed")
            except Exception as e:
                log.error(f"Error stopping API server: {e}")
            finally:
                self.api_server_process = None
    
    def start_all(self) -> bool:
        """Start all Airflow services.
        
        Returns:
            True if all services started successfully
        """
        if not self.is_airflow_installed():
            log.error("Airflow is not installed. Install with: pip install apache-airflow")
            return False
        
        # Initialize database if needed
        if not self.initialize_airflow_db():
            return False
        
        # Start scheduler
        if not self.start_scheduler():
            return False
        
        # Start API server
        if not self.start_api_server():
            self.stop_scheduler()  # Cleanup on failure
            return False
        
        log.info("All Airflow services started successfully")
        return True
    
    def stop_all(self) -> None:
        """Stop all Airflow services."""
        log.info("Stopping all Airflow services...")
        self.stop_api_server()
        self.stop_scheduler()
        log.info("All Airflow services stopped")
    
    def is_running(self) -> bool:
        """Check if Airflow services are running.
        
        Returns:
            True if both scheduler and API server are running
        """
        scheduler_running = (
            self.scheduler_process is not None
            and self.scheduler_process.poll() is None
        )
        
        api_running = (
            self.api_server_process is not None
            and self.api_server_process.poll() is None
        )
        
        return scheduler_running and api_running
    
    def get_status(self) -> Dict[str, bool]:
        """Get status of all services.
        
        Returns:
            Dict with status of scheduler and API server
        """
        return {
            "scheduler": (
                self.scheduler_process is not None
                and self.scheduler_process.poll() is None
            ),
            "api_server": (
                self.api_server_process is not None
                and self.api_server_process.poll() is None
            ),
        }
    
    def wait_for_api_ready(self, timeout: int = 30) -> bool:
        """Wait for API server to be ready.
        
        Args:
            timeout: Maximum time to wait in seconds
        
        Returns:
            True if API server is ready
        """
        import urllib.request
        import urllib.error
        
        start_time = time.time()
        url = f"http://localhost:{self.api_port}/health"
        
        while time.time() - start_time < timeout:
            try:
                req = urllib.request.Request(url)
                req.add_header('User-Agent', 'Scraper-Platform-UI')
                with urllib.request.urlopen(req, timeout=2) as response:
                    if response.status == 200:
                        log.info("API server is ready")
                        return True
            except (urllib.error.URLError, Exception):
                pass
            
            time.sleep(1)
        
        log.warning("API server did not become ready within timeout")
        return False
    
    def __del__(self) -> None:
        """Cleanup on destruction."""
        self.stop_all()

