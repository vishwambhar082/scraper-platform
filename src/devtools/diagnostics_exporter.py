"""
Comprehensive diagnostics export tool for the scraper platform.

This module provides:
- System information collection
- Platform configuration export
- Run history and logs
- Database diagnostics
- Performance metrics
- Multiple export formats (ZIP, JSON, HTML)
- PII/secret scrubbing
- CLI and UI integration
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import psutil

from src.app_logging.unified_logger import get_unified_logger
from src.common.logging_utils import get_logger
from src.common.runs_repo import RunsRepository
from src.common.settings import get_runtime_env
from src.db.schema_version import get_schema_version
from src.run_tracking.query import get_run, list_runs

log = get_logger("diagnostics-exporter")

# Size limits
MAX_BUNDLE_SIZE_MB = 50
MAX_LOG_LINES = 1000

# Patterns for secret scrubbing
SECRET_PATTERNS = [
    (re.compile(r'password["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', re.IGNORECASE), 'password=***REDACTED***'),
    (re.compile(r'token["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', re.IGNORECASE), 'token=***REDACTED***'),
    (re.compile(r'api[_-]?key["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', re.IGNORECASE), 'api_key=***REDACTED***'),
    (re.compile(r'secret["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', re.IGNORECASE), 'secret=***REDACTED***'),
    (re.compile(r'authorization["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', re.IGNORECASE), 'authorization=***REDACTED***'),
    (re.compile(r'Bearer\s+[A-Za-z0-9\-._~+/]+=*', re.IGNORECASE), 'Bearer ***REDACTED***'),
    (re.compile(r'Basic\s+[A-Za-z0-9+/]+=*', re.IGNORECASE), 'Basic ***REDACTED***'),
    # Connection strings
    (re.compile(r'postgresql://[^:]+:([^@]+)@', re.IGNORECASE), 'postgresql://user:***REDACTED***@'),
    (re.compile(r'mysql://[^:]+:([^@]+)@', re.IGNORECASE), 'mysql://user:***REDACTED***@'),
    # AWS credentials
    (re.compile(r'AKIA[0-9A-Z]{16}'), '***REDACTED_AWS_KEY***'),
    (re.compile(r'aws_secret_access_key["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', re.IGNORECASE), 'aws_secret_access_key=***REDACTED***'),
]

# Environment variables to exclude (contain secrets)
SECRET_ENV_VARS = {
    'PASSWORD', 'SECRET', 'TOKEN', 'KEY', 'CREDENTIALS', 'AUTH',
    'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN', 'DATABASE_PASSWORD',
    'DB_PASSWORD', 'POSTGRES_PASSWORD', 'MYSQL_PASSWORD',
}


class DiagnosticsExporter:
    """Collects and exports comprehensive platform diagnostics."""

    def __init__(
        self,
        output_path: Optional[Path] = None,
        format: str = "zip",
        run_id: Optional[str] = None,
    ) -> None:
        """
        Initialize the diagnostics exporter.

        Args:
            output_path: Path to export file (default: diagnostics_TIMESTAMP.{format})
            format: Export format ('zip', 'json', 'html')
            run_id: Optional run ID to filter diagnostics for specific run
        """
        self.format = format.lower()
        self.run_id = run_id

        # Generate default output path
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            suffix = "zip" if self.format == "zip" else self.format
            output_path = Path(f"diagnostics_{timestamp}.{suffix}")

        self.output_path = Path(output_path)
        self.diagnostics: Dict[str, Any] = {}
        self.temp_dir: Optional[Path] = None

        # Initialize repositories
        self.runs_repo = RunsRepository()
        self.unified_logger = get_unified_logger()

    def collect_all(self) -> Dict[str, Any]:
        """Collect all diagnostic information."""
        log.info("Starting diagnostics collection", extra={"run_id": self.run_id})

        self.diagnostics = {
            "metadata": self._collect_metadata(),
            "system": self._collect_system_info(),
            "platform": self._collect_platform_info(),
            "database": self._collect_database_info(),
            "runs": self._collect_run_history(),
            "logs": self._collect_logs(),
            "environment": self._collect_environment(),
            "packages": self._collect_installed_packages(),
            "performance": self._collect_performance_metrics(),
            "errors": self._collect_recent_errors(),
        }

        log.info("Diagnostics collection completed", extra={
            "sections": list(self.diagnostics.keys()),
            "run_id": self.run_id,
        })

        return self.diagnostics

    def _collect_metadata(self) -> Dict[str, Any]:
        """Collect metadata about the diagnostic export."""
        return {
            "exported_at": datetime.utcnow().isoformat(),
            "exporter_version": "1.0.0",
            "format": self.format,
            "run_id_filter": self.run_id,
            "platform_env": get_runtime_env(),
        }

    def _collect_system_info(self) -> Dict[str, Any]:
        """Collect system information."""
        try:
            cpu_freq = psutil.cpu_freq()
            cpu_freq_current = cpu_freq.current if cpu_freq else None

            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            return {
                "os": {
                    "system": platform.system(),
                    "release": platform.release(),
                    "version": platform.version(),
                    "machine": platform.machine(),
                    "processor": platform.processor(),
                    "platform": platform.platform(),
                },
                "python": {
                    "version": platform.python_version(),
                    "implementation": platform.python_implementation(),
                    "compiler": platform.python_compiler(),
                    "executable": sys.executable,
                },
                "cpu": {
                    "physical_cores": psutil.cpu_count(logical=False),
                    "logical_cores": psutil.cpu_count(logical=True),
                    "current_freq_mhz": cpu_freq_current,
                    "usage_percent": psutil.cpu_percent(interval=1),
                },
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "percent": memory.percent,
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent": disk.percent,
                },
            }
        except Exception as e:
            log.warning(f"Error collecting system info: {e}")
            return {"error": str(e)}

    def _collect_platform_info(self) -> Dict[str, Any]:
        """Collect platform version and configuration."""
        config = {}

        # Try to read version from common locations
        version_files = [
            Path("VERSION"),
            Path("version.txt"),
            Path(".version"),
        ]

        for vfile in version_files:
            if vfile.exists():
                try:
                    config["version"] = vfile.read_text().strip()
                    break
                except Exception:
                    pass

        # Get working directory
        config["working_directory"] = str(Path.cwd())

        # Check for key configuration files
        config_files = {
            "requirements.txt": Path("requirements.txt"),
            "pyproject.toml": Path("pyproject.toml"),
            "setup.py": Path("setup.py"),
            ".env": Path(".env"),
            "config_yaml": Path("config/env") / f"{get_runtime_env()}.yaml",
        }

        config["config_files_present"] = {
            name: path.exists() for name, path in config_files.items()
        }

        # Get git info if available
        config["git"] = self._get_git_info()

        return config

    def _get_git_info(self) -> Dict[str, Any]:
        """Get Git repository information."""
        git_info = {}

        try:
            # Check if we're in a git repo
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                # Get current branch
                result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    git_info["branch"] = result.stdout.strip()

                # Get latest commit
                result = subprocess.run(
                    ["git", "log", "-1", "--format=%H|%an|%ae|%ai|%s"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    parts = result.stdout.strip().split("|")
                    if len(parts) == 5:
                        git_info["latest_commit"] = {
                            "hash": parts[0],
                            "author": parts[1],
                            "email": parts[2],
                            "date": parts[3],
                            "message": parts[4],
                        }

                # Get status
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    git_info["has_uncommitted_changes"] = bool(result.stdout.strip())

        except Exception as e:
            log.debug(f"Git info collection failed: {e}")
            git_info["error"] = str(e)

        return git_info

    def _collect_database_info(self) -> Dict[str, Any]:
        """Collect database diagnostics."""
        db_info = {}

        try:
            # Get schema version
            schema_version = get_schema_version()
            db_info["schema_version"] = schema_version

            # Check if DB is enabled
            db_enabled = os.getenv("SCRAPER_PLATFORM_DISABLE_DB") != "1"
            db_info["enabled"] = db_enabled

            if db_enabled:
                # Get database connection info (sanitized)
                db_url = os.getenv("DATABASE_URL", "")
                if db_url:
                    # Scrub password from connection string
                    db_info["connection_string"] = self._scrub_secrets(db_url)

                # Try to get table counts (if we can connect)
                try:
                    from src.common.db import get_conn

                    conn = get_conn()
                    with conn.cursor() as cur:
                        # Get table info from scraper schema
                        cur.execute("""
                            SELECT table_name,
                                   pg_total_relation_size(quote_ident(table_name)::regclass) as size
                            FROM information_schema.tables
                            WHERE table_schema = 'scraper'
                            ORDER BY table_name
                        """)

                        tables = []
                        for row in cur.fetchall():
                            tables.append({
                                "name": row[0],
                                "size_mb": round(row[1] / (1024**2), 2) if row[1] else 0,
                            })

                        db_info["tables"] = tables
                        db_info["total_tables"] = len(tables)

                    conn.close()

                except Exception as e:
                    log.warning(f"Could not collect database table info: {e}")
                    db_info["table_info_error"] = str(e)

        except Exception as e:
            log.warning(f"Error collecting database info: {e}")
            db_info["error"] = str(e)

        return db_info

    def _collect_run_history(self) -> Dict[str, Any]:
        """Collect run history from database."""
        try:
            if self.run_id:
                # Get specific run
                run = get_run(self.run_id)
                if run:
                    return {
                        "runs": [run],
                        "total_runs": 1,
                        "filtered_by_run_id": self.run_id,
                    }
                else:
                    return {
                        "runs": [],
                        "total_runs": 0,
                        "filtered_by_run_id": self.run_id,
                        "error": "Run not found",
                    }
            else:
                # Get recent runs
                runs = list_runs(limit=50)

                # Group by source and status
                by_source = defaultdict(int)
                by_status = defaultdict(int)

                for run in runs:
                    by_source[run.get("source", "unknown")] += 1
                    by_status[run.get("status", "unknown")] += 1

                return {
                    "runs": runs,
                    "total_runs": len(runs),
                    "by_source": dict(by_source),
                    "by_status": dict(by_status),
                }

        except Exception as e:
            log.warning(f"Error collecting run history: {e}")
            return {"error": str(e)}

    def _collect_logs(self) -> Dict[str, Any]:
        """Collect recent logs."""
        logs_data = {
            "total_lines": 0,
            "error_count": 0,
            "warning_count": 0,
            "recent_logs": [],
        }

        try:
            # Get logs from unified logger
            filters = {}
            if self.run_id:
                filters["run_id"] = self.run_id

            filters["limit"] = MAX_LOG_LINES

            recent_logs = self.unified_logger.search(**filters)

            # Scrub secrets from logs
            for log_entry in recent_logs:
                if "message" in log_entry:
                    log_entry["message"] = self._scrub_secrets(log_entry["message"])
                if "metadata" in log_entry and isinstance(log_entry["metadata"], dict):
                    log_entry["metadata"] = self._scrub_dict(log_entry["metadata"])

            logs_data["recent_logs"] = recent_logs
            logs_data["total_lines"] = len(recent_logs)

            # Count by level
            for entry in recent_logs:
                level = entry.get("level", "").upper()
                if level == "ERROR":
                    logs_data["error_count"] += 1
                elif level == "WARNING":
                    logs_data["warning_count"] += 1

            # Also collect from log files if available
            log_file_paths = [
                Path("logs/unified_logs.jsonl"),
                Path("logs/scraper.log"),
                Path("logs/ui_logs.json"),
            ]

            logs_data["log_files"] = {}
            for log_path in log_file_paths:
                if log_path.exists():
                    try:
                        size_mb = log_path.stat().st_size / (1024**2)
                        logs_data["log_files"][str(log_path)] = {
                            "exists": True,
                            "size_mb": round(size_mb, 2),
                        }
                    except Exception:
                        logs_data["log_files"][str(log_path)] = {
                            "exists": True,
                            "size_mb": None,
                        }
                else:
                    logs_data["log_files"][str(log_path)] = {
                        "exists": False,
                    }

        except Exception as e:
            log.warning(f"Error collecting logs: {e}")
            logs_data["error"] = str(e)

        return logs_data

    def _collect_environment(self) -> Dict[str, Any]:
        """Collect environment variables (sanitized)."""
        env_data = {
            "variables": {},
            "count": 0,
            "redacted_count": 0,
        }

        try:
            for key, value in os.environ.items():
                # Check if this env var should be redacted
                should_redact = any(secret in key.upper() for secret in SECRET_ENV_VARS)

                if should_redact:
                    env_data["variables"][key] = "***REDACTED***"
                    env_data["redacted_count"] += 1
                else:
                    # Still scrub any secrets that might be in the value
                    env_data["variables"][key] = self._scrub_secrets(value)

                env_data["count"] += 1

        except Exception as e:
            log.warning(f"Error collecting environment: {e}")
            env_data["error"] = str(e)

        return env_data

    def _collect_installed_packages(self) -> Dict[str, Any]:
        """Collect installed Python packages."""
        packages_data = {
            "packages": [],
            "total_count": 0,
        }

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "freeze"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                packages = []

                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        packages.append(line)

                packages_data["packages"] = packages
                packages_data["total_count"] = len(packages)
            else:
                packages_data["error"] = f"pip freeze failed: {result.stderr}"

        except Exception as e:
            log.warning(f"Error collecting packages: {e}")
            packages_data["error"] = str(e)

        return packages_data

    def _collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect recent performance metrics."""
        metrics = {
            "current_cpu_percent": None,
            "current_memory_percent": None,
            "process_info": {},
        }

        try:
            # Current system metrics
            metrics["current_cpu_percent"] = psutil.cpu_percent(interval=1)
            metrics["current_memory_percent"] = psutil.virtual_memory().percent

            # Current process info
            process = psutil.Process()
            metrics["process_info"] = {
                "pid": process.pid,
                "cpu_percent": process.cpu_percent(interval=0.1),
                "memory_mb": round(process.memory_info().rss / (1024**2), 2),
                "threads": process.num_threads(),
                "create_time": datetime.fromtimestamp(process.create_time()).isoformat(),
            }

            # Try to get run performance stats
            if self.run_id:
                run = get_run(self.run_id)
                if run:
                    metrics["run_performance"] = {
                        "duration_seconds": run.get("duration_seconds"),
                        "status": run.get("status"),
                        "stats": run.get("stats"),
                    }

        except Exception as e:
            log.warning(f"Error collecting performance metrics: {e}")
            metrics["error"] = str(e)

        return metrics

    def _collect_recent_errors(self) -> Dict[str, Any]:
        """Collect recent error logs."""
        errors_data = {
            "errors": [],
            "total_count": 0,
        }

        try:
            # Get error-level logs
            filters = {"level": "ERROR", "limit": 100}
            if self.run_id:
                filters["run_id"] = self.run_id

            error_logs = self.unified_logger.search(**filters)

            # Scrub secrets
            for error in error_logs:
                if "message" in error:
                    error["message"] = self._scrub_secrets(error["message"])
                if "metadata" in error and isinstance(error["metadata"], dict):
                    error["metadata"] = self._scrub_dict(error["metadata"])

            errors_data["errors"] = error_logs
            errors_data["total_count"] = len(error_logs)

        except Exception as e:
            log.warning(f"Error collecting recent errors: {e}")
            errors_data["error"] = str(e)

        return errors_data

    def _scrub_secrets(self, text: str) -> str:
        """Scrub secrets from text using regex patterns."""
        if not isinstance(text, str):
            return text

        result = text
        for pattern, replacement in SECRET_PATTERNS:
            result = pattern.sub(replacement, result)

        return result

    def _scrub_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively scrub secrets from dictionary."""
        if not isinstance(data, dict):
            return data

        result = {}
        for key, value in data.items():
            # Check if key contains secret-like terms
            key_lower = key.lower()
            is_secret_key = any(secret.lower() in key_lower for secret in SECRET_ENV_VARS)

            if is_secret_key:
                result[key] = "***REDACTED***"
            elif isinstance(value, str):
                result[key] = self._scrub_secrets(value)
            elif isinstance(value, dict):
                result[key] = self._scrub_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self._scrub_dict(item) if isinstance(item, dict)
                    else self._scrub_secrets(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                result[key] = value

        return result

    def export(self) -> Path:
        """
        Export diagnostics in the specified format.

        Returns:
            Path to the exported file
        """
        # Collect diagnostics
        self.collect_all()

        # Export based on format
        if self.format == "json":
            return self._export_json()
        elif self.format == "html":
            return self._export_html()
        else:  # default to zip
            return self._export_zip()

    def _export_json(self) -> Path:
        """Export diagnostics as JSON file."""
        log.info(f"Exporting diagnostics to JSON: {self.output_path}")

        # Scrub entire diagnostics dict
        scrubbed = self._scrub_dict(self.diagnostics)

        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(scrubbed, f, indent=2, default=str)

        size_mb = self.output_path.stat().st_size / (1024**2)
        log.info(f"JSON export complete: {self.output_path} ({size_mb:.2f} MB)")

        return self.output_path

    def _export_html(self) -> Path:
        """Export diagnostics as HTML report."""
        log.info(f"Exporting diagnostics to HTML: {self.output_path}")

        # Scrub entire diagnostics dict
        scrubbed = self._scrub_dict(self.diagnostics)

        html = self._generate_html_report(scrubbed)

        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        size_mb = self.output_path.stat().st_size / (1024**2)
        log.info(f"HTML export complete: {self.output_path} ({size_mb:.2f} MB)")

        return self.output_path

    def _export_zip(self) -> Path:
        """Export diagnostics as ZIP bundle."""
        log.info(f"Exporting diagnostics to ZIP: {self.output_path}")

        # Create temporary directory for files
        import tempfile
        self.temp_dir = Path(tempfile.mkdtemp())

        try:
            # Scrub entire diagnostics dict
            scrubbed = self._scrub_dict(self.diagnostics)

            # Write diagnostics.json
            diagnostics_json = self.temp_dir / "diagnostics.json"
            with open(diagnostics_json, 'w', encoding='utf-8') as f:
                json.dump(scrubbed, f, indent=2, default=str)

            # Write individual sections as separate files
            sections_dir = self.temp_dir / "sections"
            sections_dir.mkdir()

            for section_name, section_data in scrubbed.items():
                section_file = sections_dir / f"{section_name}.json"
                with open(section_file, 'w', encoding='utf-8') as f:
                    json.dump(section_data, f, indent=2, default=str)

            # Generate HTML report
            html_report = self.temp_dir / "report.html"
            with open(html_report, 'w', encoding='utf-8') as f:
                f.write(self._generate_html_report(scrubbed))

            # Copy log files (last N lines, scrubbed)
            logs_dir = self.temp_dir / "logs"
            logs_dir.mkdir()

            log_files = [
                Path("logs/unified_logs.jsonl"),
                Path("logs/scraper.log"),
            ]

            for log_file in log_files:
                if log_file.exists():
                    try:
                        self._copy_log_file(log_file, logs_dir / log_file.name)
                    except Exception as e:
                        log.warning(f"Could not copy log file {log_file}: {e}")

            # Create ZIP archive
            with zipfile.ZipFile(self.output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in self.temp_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(self.temp_dir)
                        zipf.write(file_path, arcname)

            # Check size
            size_mb = self.output_path.stat().st_size / (1024**2)
            if size_mb > MAX_BUNDLE_SIZE_MB:
                log.warning(f"ZIP bundle exceeds size limit: {size_mb:.2f} MB > {MAX_BUNDLE_SIZE_MB} MB")

            log.info(f"ZIP export complete: {self.output_path} ({size_mb:.2f} MB)")

            return self.output_path

        finally:
            # Cleanup temp directory
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)

    def _copy_log_file(self, source: Path, dest: Path) -> None:
        """Copy log file with scrubbing and line limits."""
        lines = []

        # Read last N lines
        with open(source, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            lines = all_lines[-MAX_LOG_LINES:]

        # Scrub and write
        with open(dest, 'w', encoding='utf-8') as f:
            for line in lines:
                scrubbed_line = self._scrub_secrets(line)
                f.write(scrubbed_line)

    def _generate_html_report(self, data: Dict[str, Any]) -> str:
        """Generate HTML report from diagnostics data."""
        metadata = data.get("metadata", {})
        system = data.get("system", {})
        platform_info = data.get("platform", {})
        database = data.get("database", {})
        runs = data.get("runs", {})
        logs = data.get("logs", {})
        environment = data.get("environment", {})
        packages = data.get("packages", {})
        performance = data.get("performance", {})
        errors = data.get("errors", {})

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Scraper Platform Diagnostics Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            border-bottom: 2px solid #ddd;
            padding-bottom: 5px;
            margin-top: 30px;
        }}
        h3 {{
            color: #666;
            margin-top: 20px;
        }}
        .section {{
            background: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metadata {{
            background: #e3f2fd;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: 600;
        }}
        .badge-success {{
            background: #d4edda;
            color: #155724;
        }}
        .badge-error {{
            background: #f8d7da;
            color: #721c24;
        }}
        .badge-warning {{
            background: #fff3cd;
            color: #856404;
        }}
        .badge-info {{
            background: #d1ecf1;
            color: #0c5460;
        }}
        pre {{
            background: #f8f9fa;
            padding: 10px;
            border-radius: 3px;
            overflow-x: auto;
        }}
        code {{
            background: #f8f9fa;
            padding: 2px 5px;
            border-radius: 3px;
            font-family: "Monaco", "Menlo", "Ubuntu Mono", monospace;
        }}
        .metric {{
            display: inline-block;
            margin: 10px 20px 10px 0;
        }}
        .metric-label {{
            color: #666;
            font-size: 14px;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: 600;
            color: #333;
        }}
    </style>
</head>
<body>
    <h1>Scraper Platform Diagnostics Report</h1>

    <div class="metadata">
        <strong>Generated:</strong> {metadata.get('exported_at', 'N/A')}<br>
        <strong>Format:</strong> {metadata.get('format', 'N/A')}<br>
        <strong>Environment:</strong> {metadata.get('platform_env', 'N/A')}<br>
        <strong>Run ID Filter:</strong> {metadata.get('run_id_filter') or 'None (all runs)'}
    </div>

    <div class="section">
        <h2>System Information</h2>
        <h3>Operating System</h3>
        <table>
            <tr><th>Property</th><th>Value</th></tr>
            <tr><td>System</td><td>{system.get('os', {}).get('system', 'N/A')}</td></tr>
            <tr><td>Release</td><td>{system.get('os', {}).get('release', 'N/A')}</td></tr>
            <tr><td>Platform</td><td>{system.get('os', {}).get('platform', 'N/A')}</td></tr>
            <tr><td>Processor</td><td>{system.get('os', {}).get('processor', 'N/A')}</td></tr>
        </table>

        <h3>Python</h3>
        <table>
            <tr><th>Property</th><th>Value</th></tr>
            <tr><td>Version</td><td>{system.get('python', {}).get('version', 'N/A')}</td></tr>
            <tr><td>Implementation</td><td>{system.get('python', {}).get('implementation', 'N/A')}</td></tr>
            <tr><td>Executable</td><td>{system.get('python', {}).get('executable', 'N/A')}</td></tr>
        </table>

        <h3>Hardware</h3>
        <div class="metric">
            <div class="metric-label">CPU Cores</div>
            <div class="metric-value">{system.get('cpu', {}).get('logical_cores', 'N/A')}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Memory (GB)</div>
            <div class="metric-value">{system.get('memory', {}).get('total_gb', 'N/A')}</div>
        </div>
        <div class="metric">
            <div class="metric-label">CPU Usage (%)</div>
            <div class="metric-value">{system.get('cpu', {}).get('usage_percent', 'N/A')}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Memory Usage (%)</div>
            <div class="metric-value">{system.get('memory', {}).get('percent', 'N/A')}</div>
        </div>
    </div>

    <div class="section">
        <h2>Platform Information</h2>
        <table>
            <tr><th>Property</th><th>Value</th></tr>
            <tr><td>Working Directory</td><td>{platform_info.get('working_directory', 'N/A')}</td></tr>
            <tr><td>Git Branch</td><td>{platform_info.get('git', {}).get('branch', 'N/A')}</td></tr>
            <tr><td>Uncommitted Changes</td><td>{platform_info.get('git', {}).get('has_uncommitted_changes', 'N/A')}</td></tr>
        </table>
    </div>

    <div class="section">
        <h2>Database</h2>
        <table>
            <tr><th>Property</th><th>Value</th></tr>
            <tr><td>Enabled</td><td>{database.get('enabled', 'N/A')}</td></tr>
            <tr><td>Schema Version</td><td>{database.get('schema_version', 'N/A')}</td></tr>
            <tr><td>Total Tables</td><td>{database.get('total_tables', 'N/A')}</td></tr>
        </table>
    </div>

    <div class="section">
        <h2>Run History</h2>
        <div class="metric">
            <div class="metric-label">Total Runs</div>
            <div class="metric-value">{runs.get('total_runs', 0)}</div>
        </div>

        <h3>By Status</h3>
        <table>
            <tr><th>Status</th><th>Count</th></tr>
            {''.join(f'<tr><td>{status}</td><td>{count}</td></tr>' for status, count in runs.get('by_status', {}).items())}
        </table>

        <h3>By Source</h3>
        <table>
            <tr><th>Source</th><th>Count</th></tr>
            {''.join(f'<tr><td>{source}</td><td>{count}</td></tr>' for source, count in runs.get('by_source', {}).items())}
        </table>
    </div>

    <div class="section">
        <h2>Logs Summary</h2>
        <div class="metric">
            <div class="metric-label">Total Lines</div>
            <div class="metric-value">{logs.get('total_lines', 0)}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Errors</div>
            <div class="metric-value">{logs.get('error_count', 0)}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Warnings</div>
            <div class="metric-value">{logs.get('warning_count', 0)}</div>
        </div>

        <h3>Log Files</h3>
        <table>
            <tr><th>File</th><th>Exists</th><th>Size (MB)</th></tr>
            {''.join(f'<tr><td>{file_path}</td><td>{info.get("exists", False)}</td><td>{info.get("size_mb", "N/A")}</td></tr>' for file_path, info in logs.get('log_files', {}).items())}
        </table>
    </div>

    <div class="section">
        <h2>Performance Metrics</h2>
        <div class="metric">
            <div class="metric-label">CPU %</div>
            <div class="metric-value">{performance.get('current_cpu_percent', 'N/A')}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Memory %</div>
            <div class="metric-value">{performance.get('current_memory_percent', 'N/A')}</div>
        </div>

        <h3>Process Info</h3>
        <table>
            <tr><th>Property</th><th>Value</th></tr>
            <tr><td>PID</td><td>{performance.get('process_info', {}).get('pid', 'N/A')}</td></tr>
            <tr><td>CPU %</td><td>{performance.get('process_info', {}).get('cpu_percent', 'N/A')}</td></tr>
            <tr><td>Memory (MB)</td><td>{performance.get('process_info', {}).get('memory_mb', 'N/A')}</td></tr>
            <tr><td>Threads</td><td>{performance.get('process_info', {}).get('threads', 'N/A')}</td></tr>
        </table>
    </div>

    <div class="section">
        <h2>Recent Errors</h2>
        <p><strong>Total Errors:</strong> {errors.get('total_count', 0)}</p>
        {self._format_errors_html(errors.get('errors', [])[:10])}
    </div>

    <div class="section">
        <h2>Installed Packages</h2>
        <p><strong>Total Packages:</strong> {packages.get('total_count', 0)}</p>
        <pre>{chr(10).join(packages.get('packages', [])[:50])}</pre>
        {f'<p><em>...and {packages.get("total_count", 0) - 50} more packages</em></p>' if packages.get('total_count', 0) > 50 else ''}
    </div>

    <div class="section">
        <h2>Environment Variables</h2>
        <p><strong>Total Variables:</strong> {environment.get('count', 0)}</p>
        <p><strong>Redacted:</strong> {environment.get('redacted_count', 0)}</p>
    </div>

    <footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666;">
        <p>Generated by Scraper Platform Diagnostics Exporter v{metadata.get('exporter_version', '1.0.0')}</p>
    </footer>
</body>
</html>"""

        return html

    def _format_errors_html(self, errors: List[Dict[str, Any]]) -> str:
        """Format error logs as HTML."""
        if not errors:
            return "<p><em>No recent errors</em></p>"

        html_parts = ['<table>', '<tr><th>Timestamp</th><th>Logger</th><th>Message</th></tr>']

        for error in errors:
            timestamp = error.get('timestamp', 'N/A')
            logger = error.get('logger', 'N/A')
            message = error.get('message', 'N/A')

            # Escape HTML
            message = message.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

            html_parts.append(f'<tr><td>{timestamp}</td><td>{logger}</td><td>{message}</td></tr>')

        html_parts.append('</table>')
        return ''.join(html_parts)


def main() -> None:
    """CLI entry point for diagnostics exporter."""
    parser = argparse.ArgumentParser(
        description="Export comprehensive platform diagnostics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export as ZIP bundle (default)
  python -m src.devtools.diagnostics_exporter --output ./diagnostics.zip

  # Export as JSON for programmatic access
  python -m src.devtools.diagnostics_exporter --format json --output diagnostics.json

  # Export as HTML report
  python -m src.devtools.diagnostics_exporter --format html --output report.html

  # Export diagnostics for specific run
  python -m src.devtools.diagnostics_exporter --run-id RUN-20251213-ABC123 --format html
        """
    )

    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output file path (default: diagnostics_TIMESTAMP.{format})",
    )

    parser.add_argument(
        "--format", "-f",
        choices=["zip", "json", "html"],
        default="zip",
        help="Export format (default: zip)",
    )

    parser.add_argument(
        "--run-id", "-r",
        type=str,
        help="Filter diagnostics for specific run ID",
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        # Create exporter
        exporter = DiagnosticsExporter(
            output_path=args.output,
            format=args.format,
            run_id=args.run_id,
        )

        # Export diagnostics
        output_file = exporter.export()

        print(f"\n✓ Diagnostics exported successfully!")
        print(f"  Output: {output_file.absolute()}")
        print(f"  Size: {output_file.stat().st_size / (1024**2):.2f} MB")

        if args.format == "zip":
            print(f"\nZIP contents:")
            print(f"  - diagnostics.json (complete diagnostics)")
            print(f"  - sections/*.json (individual sections)")
            print(f"  - report.html (HTML report)")
            print(f"  - logs/* (recent log files)")

    except Exception as e:
        log.error(f"Export failed: {e}", exc_info=True)
        print(f"\n✗ Export failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
