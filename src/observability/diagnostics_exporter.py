"""
Diagnostics export for troubleshooting.
"""

import zipfile
import json
import logging
import platform
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import psutil

logger = logging.getLogger(__name__)


class DiagnosticsExporter:
    """
    Export complete diagnostics bundle for troubleshooting.

    Includes:
    - System information
    - Application logs
    - Configuration files
    - Recent execution history
    - Performance metrics
    - Database snapshots
    """

    def __init__(
        self,
        output_dir: Path,
        logs_dir: Path,
        config_dir: Path,
        db_dir: Path
    ):
        """
        Initialize diagnostics exporter.

        Args:
            output_dir: Where to save diagnostic bundles
            logs_dir: Application logs directory
            config_dir: Configuration files directory
            db_dir: Database files directory
        """
        self.output_dir = output_dir
        self.logs_dir = logs_dir
        self.config_dir = config_dir
        self.db_dir = db_dir

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_bundle(
        self,
        include_logs: bool = True,
        include_config: bool = True,
        include_db_snapshot: bool = True,
        include_metrics: bool = True,
        execution_engine_stats: Optional[Dict[str, Any]] = None,
        scheduler_stats: Optional[Dict[str, Any]] = None,
        recent_errors: Optional[List[str]] = None
    ) -> Path:
        """
        Create diagnostics ZIP bundle.

        Args:
            include_logs: Include log files
            include_config: Include config files
            include_db_snapshot: Include database snapshots
            include_metrics: Include system metrics
            execution_engine_stats: Current engine stats
            scheduler_stats: Current scheduler stats
            recent_errors: Recent error messages

        Returns:
            Path to created ZIP file
        """
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        bundle_name = f"diagnostics_{timestamp}.zip"
        bundle_path = self.output_dir / bundle_name

        logger.info(f"Creating diagnostics bundle: {bundle_path}")

        with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # System information
            self._add_system_info(zipf)

            # Application metadata
            self._add_app_metadata(
                zipf,
                execution_engine_stats,
                scheduler_stats,
                recent_errors
            )

            # System metrics
            if include_metrics:
                self._add_system_metrics(zipf)

            # Logs
            if include_logs:
                self._add_logs(zipf)

            # Configuration
            if include_config:
                self._add_config(zipf)

            # Database snapshots
            if include_db_snapshot:
                self._add_db_snapshots(zipf)

            # Manifest
            self._add_manifest(zipf, timestamp)

        logger.info(f"Diagnostics bundle created: {bundle_path} ({bundle_path.stat().st_size} bytes)")
        return bundle_path

    def _add_system_info(self, zipf: zipfile.ZipFile):
        """Add system information."""
        system_info = {
            'platform': platform.platform(),
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'python_version': sys.version,
            'python_executable': sys.executable,
            'cpu_count': psutil.cpu_count(),
            'memory_total_gb': psutil.virtual_memory().total / (1024 ** 3),
        }

        zipf.writestr(
            'system_info.json',
            json.dumps(system_info, indent=2)
        )

    def _add_app_metadata(
        self,
        zipf: zipfile.ZipFile,
        execution_engine_stats: Optional[Dict[str, Any]],
        scheduler_stats: Optional[Dict[str, Any]],
        recent_errors: Optional[List[str]]
    ):
        """Add application state metadata."""
        metadata = {
            'export_timestamp': datetime.utcnow().isoformat(),
            'execution_engine': execution_engine_stats or {},
            'scheduler': scheduler_stats or {},
            'recent_errors': recent_errors or []
        }

        zipf.writestr(
            'app_metadata.json',
            json.dumps(metadata, indent=2)
        )

    def _add_system_metrics(self, zipf: zipfile.ZipFile):
        """Add current system metrics snapshot."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            metrics = {
                'timestamp': datetime.utcnow().isoformat(),
                'cpu': {
                    'percent': cpu_percent,
                    'count': psutil.cpu_count(),
                    'freq_mhz': psutil.cpu_freq().current if psutil.cpu_freq() else None
                },
                'memory': {
                    'total_mb': memory.total / (1024 ** 2),
                    'available_mb': memory.available / (1024 ** 2),
                    'used_mb': memory.used / (1024 ** 2),
                    'percent': memory.percent
                },
                'disk': {
                    'total_gb': disk.total / (1024 ** 3),
                    'used_gb': disk.used / (1024 ** 3),
                    'free_gb': disk.free / (1024 ** 3),
                    'percent': disk.percent
                },
                'process': self._get_process_metrics()
            }

            zipf.writestr(
                'system_metrics.json',
                json.dumps(metrics, indent=2)
            )
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")

    def _get_process_metrics(self) -> Dict[str, Any]:
        """Get current process metrics."""
        try:
            process = psutil.Process()
            return {
                'cpu_percent': process.cpu_percent(interval=0.1),
                'memory_mb': process.memory_info().rss / (1024 ** 2),
                'num_threads': process.num_threads(),
                'num_fds': process.num_fds() if hasattr(process, 'num_fds') else None,
                'create_time': datetime.fromtimestamp(process.create_time()).isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get process metrics: {e}")
            return {}

    def _add_logs(self, zipf: zipfile.ZipFile):
        """Add log files."""
        if not self.logs_dir.exists():
            logger.warning(f"Logs directory not found: {self.logs_dir}")
            return

        try:
            for log_file in self.logs_dir.glob('*.log'):
                # Add recent logs (last 10000 lines)
                try:
                    lines = log_file.read_text(encoding='utf-8', errors='ignore').splitlines()
                    recent_lines = lines[-10000:] if len(lines) > 10000 else lines

                    zipf.writestr(
                        f"logs/{log_file.name}",
                        '\n'.join(recent_lines)
                    )
                    logger.debug(f"Added log file: {log_file.name}")
                except Exception as e:
                    logger.error(f"Failed to add log {log_file.name}: {e}")

        except Exception as e:
            logger.error(f"Failed to add logs: {e}")

    def _add_config(self, zipf: zipfile.ZipFile):
        """Add configuration files."""
        if not self.config_dir.exists():
            logger.warning(f"Config directory not found: {self.config_dir}")
            return

        try:
            for config_file in self.config_dir.glob('*.json'):
                try:
                    # Sanitize sensitive data
                    config_data = json.loads(config_file.read_text())
                    sanitized = self._sanitize_config(config_data)

                    zipf.writestr(
                        f"config/{config_file.name}",
                        json.dumps(sanitized, indent=2)
                    )
                    logger.debug(f"Added config file: {config_file.name}")
                except Exception as e:
                    logger.error(f"Failed to add config {config_file.name}: {e}")

            # Also add YAML configs
            for config_file in self.config_dir.glob('*.yaml'):
                try:
                    zipf.write(config_file, f"config/{config_file.name}")
                except Exception as e:
                    logger.error(f"Failed to add config {config_file.name}: {e}")

        except Exception as e:
            logger.error(f"Failed to add configs: {e}")

    def _sanitize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize configuration by masking sensitive values.

        Args:
            config: Configuration dict

        Returns:
            Sanitized configuration
        """
        sensitive_keys = {
            'password', 'secret', 'token', 'api_key',
            'access_key', 'private_key', 'credential'
        }

        sanitized = {}
        for key, value in config.items():
            key_lower = key.lower()

            # Check if key contains sensitive terms
            is_sensitive = any(term in key_lower for term in sensitive_keys)

            if is_sensitive and isinstance(value, str):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_config(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_config(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value

        return sanitized

    def _add_db_snapshots(self, zipf: zipfile.ZipFile):
        """Add database snapshots (schema only, not full data)."""
        if not self.db_dir.exists():
            logger.warning(f"Database directory not found: {self.db_dir}")
            return

        try:
            for db_file in self.db_dir.glob('*.db'):
                try:
                    # Get schema and basic stats
                    schema_info = self._get_db_schema(db_file)

                    zipf.writestr(
                        f"db_schemas/{db_file.stem}_schema.json",
                        json.dumps(schema_info, indent=2)
                    )
                    logger.debug(f"Added DB schema: {db_file.name}")
                except Exception as e:
                    logger.error(f"Failed to add DB schema {db_file.name}: {e}")

        except Exception as e:
            logger.error(f"Failed to add DB snapshots: {e}")

    def _get_db_schema(self, db_path: Path) -> Dict[str, Any]:
        """
        Get database schema information.

        Args:
            db_path: Path to SQLite database

        Returns:
            Schema information dict
        """
        try:
            import sqlite3

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Get table list
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            schema_info = {
                'database': db_path.name,
                'tables': {}
            }

            # Get schema for each table
            for table in tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [
                    {
                        'name': row[1],
                        'type': row[2],
                        'notnull': bool(row[3]),
                        'pk': bool(row[5])
                    }
                    for row in cursor.fetchall()
                ]

                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                row_count = cursor.fetchone()[0]

                schema_info['tables'][table] = {
                    'columns': columns,
                    'row_count': row_count
                }

            conn.close()
            return schema_info

        except Exception as e:
            logger.error(f"Failed to get DB schema for {db_path}: {e}")
            return {'error': str(e)}

    def _add_manifest(self, zipf: zipfile.ZipFile, timestamp: str):
        """Add manifest file."""
        manifest = {
            'export_timestamp': timestamp,
            'exporter_version': '1.0.0',
            'contents': [name for name in zipf.namelist()]
        }

        zipf.writestr(
            'MANIFEST.json',
            json.dumps(manifest, indent=2)
        )

    def list_bundles(self) -> List[Dict[str, Any]]:
        """
        List all diagnostic bundles.

        Returns:
            List of bundle metadata
        """
        bundles = []

        for bundle_file in sorted(self.output_dir.glob('diagnostics_*.zip'), reverse=True):
            try:
                stat = bundle_file.stat()
                bundles.append({
                    'filename': bundle_file.name,
                    'path': str(bundle_file),
                    'size_mb': stat.st_size / (1024 ** 2),
                    'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat()
                })
            except Exception as e:
                logger.error(f"Failed to stat bundle {bundle_file}: {e}")

        return bundles

    def delete_bundle(self, filename: str) -> bool:
        """
        Delete diagnostic bundle.

        Args:
            filename: Bundle filename

        Returns:
            True if deleted, False otherwise
        """
        bundle_path = self.output_dir / filename

        if not bundle_path.exists():
            logger.warning(f"Bundle not found: {filename}")
            return False

        try:
            bundle_path.unlink()
            logger.info(f"Deleted bundle: {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete bundle {filename}: {e}")
            return False

    def cleanup_old_bundles(self, keep_count: int = 10):
        """
        Delete old diagnostic bundles, keeping only recent N.

        Args:
            keep_count: Number of bundles to keep
        """
        bundles = sorted(
            self.output_dir.glob('diagnostics_*.zip'),
            key=lambda p: p.stat().st_ctime,
            reverse=True
        )

        if len(bundles) <= keep_count:
            return

        to_delete = bundles[keep_count:]
        for bundle in to_delete:
            try:
                bundle.unlink()
                logger.info(f"Cleaned up old bundle: {bundle.name}")
            except Exception as e:
                logger.error(f"Failed to delete bundle {bundle.name}: {e}")
