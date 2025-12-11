"""
Unified logging framework with JSON structured logs, search, and timeline visualization.

This module provides:
- JSON structured logging
- Human-readable logging
- Indexed by job/task/time
- Persisted locally
- Search and filter capabilities
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.common.logging_utils import JsonLogFormatter, get_logger

log = get_logger("unified-logger")


class UnifiedLogger:
    """Unified logging system with persistence and search capabilities."""
    
    def __init__(self, db_path: Optional[Path] = None) -> None:
        """Initialize the unified logger.
        
        Args:
            db_path: Path to SQLite database for log storage
        """
        if db_path is None:
            db_path = Path("logs/unified_logs.db")
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # Setup file handler for JSON logs
        self.json_log_file = self.db_path.parent / "unified_logs.jsonl"
        self.file_handler = logging.FileHandler(self.json_log_file)
        self.file_handler.setFormatter(JsonLogFormatter())
        
        # Add handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(self.file_handler)
    
    def _init_database(self) -> None:
        """Initialize the SQLite database for log storage."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                logger TEXT,
                message TEXT NOT NULL,
                job_id TEXT,
                task_id TEXT,
                source TEXT,
                run_id TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON logs(timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_job_id ON logs(job_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_id ON logs(task_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_source ON logs(source)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_level ON logs(level)
        """)
        
        conn.commit()
        conn.close()
    
    def log(
        self,
        level: str,
        message: str,
        logger: Optional[str] = None,
        job_id: Optional[str] = None,
        task_id: Optional[str] = None,
        source: Optional[str] = None,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a message with structured data.
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            logger: Logger name
            job_id: Job ID
            task_id: Task ID
            source: Source name
            run_id: Run ID
            metadata: Additional metadata
        """
        timestamp = datetime.utcnow().isoformat()
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO logs (timestamp, level, logger, message, job_id, task_id, source, run_id, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp,
            level,
            logger,
            message,
            job_id,
            task_id,
            source,
            run_id,
            json.dumps(metadata) if metadata else None,
        ))
        
        conn.commit()
        conn.close()
        
        # Also log via standard logging
        logger_obj = logging.getLogger(logger or "root")
        log_method = getattr(logger_obj, level.lower(), logger_obj.info)
        log_method(message, extra={
            "job_id": job_id,
            "task_id": task_id,
            "source": source,
            "run_id": run_id,
            **(metadata or {}),
        })
    
    def search(
        self,
        query: Optional[str] = None,
        level: Optional[str] = None,
        job_id: Optional[str] = None,
        task_id: Optional[str] = None,
        source: Optional[str] = None,
        run_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Search logs with filters.
        
        Args:
            query: Text search in message
            level: Filter by log level
            job_id: Filter by job ID
            task_id: Filter by task ID
            source: Filter by source
            run_id: Filter by run ID
            start_time: Start time filter
            end_time: End time filter
            limit: Maximum number of results
        
        Returns:
            List of log entries matching the criteria
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        conditions = []
        params = []
        
        if query:
            conditions.append("message LIKE ?")
            params.append(f"%{query}%")
        
        if level:
            conditions.append("level = ?")
            params.append(level)
        
        if job_id:
            conditions.append("job_id = ?")
            params.append(job_id)
        
        if task_id:
            conditions.append("task_id = ?")
            params.append(task_id)
        
        if source:
            conditions.append("source = ?")
            params.append(source)
        
        if run_id:
            conditions.append("run_id = ?")
            params.append(run_id)
        
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time.isoformat())
        
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time.isoformat())
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        sql = f"""
            SELECT timestamp, level, logger, message, job_id, task_id, source, run_id, metadata
            FROM logs
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ?
        """
        
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            results.append({
                "timestamp": row[0],
                "level": row[1],
                "logger": row[2],
                "message": row[3],
                "job_id": row[4],
                "task_id": row[5],
                "source": row[6],
                "run_id": row[7],
                "metadata": json.loads(row[8]) if row[8] else {},
            })
        
        return results
    
    def get_timeline(
        self,
        job_id: Optional[str] = None,
        run_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get timeline of events for visualization.
        
        Args:
            job_id: Filter by job ID
            run_id: Filter by run ID
            start_time: Start time
            end_time: End time
        
        Returns:
            List of timeline events
        """
        return self.search(
            job_id=job_id,
            run_id=run_id,
            start_time=start_time,
            end_time=end_time,
            limit=10000,
        )
    
    def export_csv(self, filepath: Path, filters: Optional[Dict[str, Any]] = None) -> None:
        """Export logs to CSV file.
        
        Args:
            filepath: Output CSV file path
            filters: Optional search filters
        """
        import csv
        
        logs = self.search(**(filters or {}))
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            if not logs:
                return
            
            writer = csv.DictWriter(f, fieldnames=logs[0].keys())
            writer.writeheader()
            writer.writerows(logs)
    
    def export_json(self, filepath: Path, filters: Optional[Dict[str, Any]] = None) -> None:
        """Export logs to JSON file.
        
        Args:
            filepath: Output JSON file path
            filters: Optional search filters
        """
        logs = self.search(**(filters or {}))
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, default=str)


# Global instance
_unified_logger: Optional[UnifiedLogger] = None


def get_unified_logger() -> UnifiedLogger:
    """Get the global unified logger instance."""
    global _unified_logger
    if _unified_logger is None:
        _unified_logger = UnifiedLogger()
    return _unified_logger

