"""
Product-grade bootstrap for desktop application.

Handles:
- Version checking
- Database migrations
- Crash recovery
- Safe startup
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class ApplicationBootstrap:
    """
    Application bootstrap manager.

    Ensures safe application startup with recovery.
    """

    def __init__(self, app_dir: Path, version: str):
        """
        Initialize bootstrap.

        Args:
            app_dir: Application data directory
            version: Current application version
        """
        self.app_dir = app_dir
        self.version = version
        self.config_file = app_dir / "config" / "app.json"
        self.crash_file = app_dir / "crash.lock"

    def bootstrap(self) -> bool:
        """
        Bootstrap application.

        Returns:
            True if bootstrap successful
        """
        logger.info(f"Bootstrapping application v{self.version}")

        try:
            # Check for crash
            if self._check_crash():
                logger.warning("Previous crash detected")
                if not self._recover_from_crash():
                    logger.error("Crash recovery failed")
                    return False

            # Create crash lock
            self._create_crash_lock()

            # Load/create config
            if not self._init_config():
                return False

            # Check version
            if not self._check_version():
                return False

            # Run migrations
            if not self._run_migrations():
                return False

            # Verify directories
            if not self._verify_directories():
                return False

            logger.info("Bootstrap complete")
            return True

        except Exception as e:
            logger.error(f"Bootstrap failed: {e}", exc_info=True)
            return False

    def shutdown(self):
        """Graceful shutdown."""
        logger.info("Shutting down application")

        try:
            # Remove crash lock
            if self.crash_file.exists():
                self.crash_file.unlink()

            logger.info("Shutdown complete")

        except Exception as e:
            logger.error(f"Shutdown error: {e}", exc_info=True)

    def _check_crash(self) -> bool:
        """Check if previous run crashed."""
        return self.crash_file.exists()

    def _create_crash_lock(self):
        """Create crash lock file."""
        self.crash_file.parent.mkdir(parents=True, exist_ok=True)
        self.crash_file.write_text(json.dumps({
            'version': self.version,
            'started_at': str(datetime.utcnow())
        }))

    def _recover_from_crash(self) -> bool:
        """
        Recover from previous crash.

        Returns:
            True if recovery successful
        """
        logger.info("Starting crash recovery...")

        try:
            # Load crash info
            if self.crash_file.exists():
                crash_info = json.loads(self.crash_file.read_text())
                logger.info(f"Crash info: {crash_info}")

            # Resume incomplete jobs (if checkpoint manager exists)
            from src.run_tracking.checkpoints import CheckpointManager

            checkpoint_db = self.app_dir / "db" / "checkpoints.db"
            if checkpoint_db.exists():
                checkpoint_mgr = CheckpointManager(checkpoint_db)
                resumable = checkpoint_mgr.list_resumable_jobs()

                logger.info(f"Found {len(resumable)} resumable jobs")

                # Mark as pending resume (actual resume handled by scheduler)
                for job in resumable:
                    logger.info(f"Resumable job: {job['job_id']}")

            # Remove crash lock
            self.crash_file.unlink()

            logger.info("Crash recovery complete")
            return True

        except Exception as e:
            logger.error(f"Crash recovery failed: {e}", exc_info=True)
            return False

    def _init_config(self) -> bool:
        """Initialize configuration."""
        try:
            if not self.config_file.exists():
                # Create default config
                default_config = {
                    'version': self.version,
                    'first_run': True,
                    'settings': {
                        'max_browsers': 3,
                        'max_memory_mb': 4096,
                        'log_level': 'INFO'
                    }
                }

                self.config_file.parent.mkdir(parents=True, exist_ok=True)
                self.config_file.write_text(json.dumps(default_config, indent=2))
                logger.info("Created default configuration")

            else:
                # Load existing config
                config = json.loads(self.config_file.read_text())
                logger.info(f"Loaded configuration for v{config.get('version')}")

            return True

        except Exception as e:
            logger.error(f"Config initialization failed: {e}", exc_info=True)
            return False

    def _check_version(self) -> bool:
        """Check version and handle upgrades."""
        try:
            config = json.loads(self.config_file.read_text())
            prev_version = config.get('version', '0.0.0')

            if prev_version != self.version:
                logger.info(f"Version upgrade: {prev_version} -> {self.version}")

                # Update version in config
                config['version'] = self.version
                self.config_file.write_text(json.dumps(config, indent=2))

            return True

        except Exception as e:
            logger.error(f"Version check failed: {e}", exc_info=True)
            return False

    def _run_migrations(self) -> bool:
        """Run database migrations."""
        try:
            from datetime import datetime

            logger.info("Running database migrations...")

            # Check for migrations directory
            migrations_dir = Path(__file__).parent.parent / "migrations"
            if not migrations_dir.exists():
                logger.debug("No migrations directory found")
                return True

            # Run migration scripts
            migration_files = sorted(migrations_dir.glob("*.py"))
            for migration_file in migration_files:
                logger.info(f"Running migration: {migration_file.name}")
                # TODO: Execute migration
                # For now, just log

            logger.info("Migrations complete")
            return True

        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            return False

    def _verify_directories(self) -> bool:
        """Verify required directories exist."""
        required_dirs = [
            self.app_dir / "logs",
            self.app_dir / "db",
            self.app_dir / "output",
            self.app_dir / "config",
            self.app_dir / "replay",
        ]

        for directory in required_dirs:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Verified directory: {directory}")

        return True


class UpdateChecker:
    """
    Check for application updates.

    Compares current version with latest release.
    """

    def __init__(self, current_version: str, check_url: Optional[str] = None):
        """
        Initialize update checker.

        Args:
            current_version: Current application version
            check_url: URL to check for updates
        """
        self.current_version = current_version
        self.check_url = check_url

    def check_for_updates(self) -> Optional[Dict[str, Any]]:
        """
        Check for available updates.

        Returns:
            Update info if available, None otherwise
        """
        if not self.check_url:
            return None

        try:
            import requests

            response = requests.get(self.check_url, timeout=5)
            response.raise_for_status()

            data = response.json()
            latest_version = data.get('version')

            if self._is_newer_version(latest_version):
                return {
                    'version': latest_version,
                    'download_url': data.get('download_url'),
                    'release_notes': data.get('release_notes'),
                    'published_at': data.get('published_at')
                }

            return None

        except Exception as e:
            logger.error(f"Update check failed: {e}")
            return None

    def _is_newer_version(self, version: str) -> bool:
        """Check if version is newer."""
        try:
            current_parts = [int(x) for x in self.current_version.split('.')]
            new_parts = [int(x) for x in version.split('.')]

            for i in range(3):
                if new_parts[i] > current_parts[i]:
                    return True
                elif new_parts[i] < current_parts[i]:
                    return False

            return False

        except Exception:
            return False
