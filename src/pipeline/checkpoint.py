"""
Pipeline Checkpointing System

Provides step-level checkpointing and resume capabilities for pipeline execution.
Uses SQLite-backed state store for persistence across crashes and restarts.

Author: Scraper Platform Team
Date: 2025-12-13
"""

from __future__ import annotations

import json
import pickle
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.common.logging_utils import get_logger

log = get_logger("pipeline.checkpoint")


@dataclass
class CheckpointMetadata:
    """Metadata for a pipeline checkpoint."""

    run_id: str
    source: str
    pipeline_name: str
    created_at: datetime
    updated_at: datetime
    status: str  # 'active', 'completed', 'failed', 'paused'
    total_steps: int
    completed_steps: int
    environment: str = "prod"
    run_type: str = "FULL_REFRESH"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "run_id": self.run_id,
            "source": self.source,
            "pipeline_name": self.pipeline_name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "environment": self.environment,
            "run_type": self.run_type,
        }


@dataclass
class StepCheckpoint:
    """Checkpoint for a single pipeline step."""

    step_id: str
    status: str  # 'pending', 'running', 'completed', 'failed', 'skipped'
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    output: Optional[Any] = None  # Serialized output
    error: Optional[str] = None
    attempt: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


class CheckpointStore:
    """SQLite-backed checkpoint storage for pipeline execution state.

    Features:
    - Step-level state persistence
    - Resume from last successful step
    - Automatic cleanup of stale checkpoints
    - Thread-safe operations
    - Crash recovery
    """

    def __init__(self, db_path: Optional[str] = None):
        """Initialize checkpoint store.

        Args:
            db_path: Path to SQLite database. Defaults to './data/checkpoints.db'
        """
        self.db_path = Path(db_path or "./data/checkpoints.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()
        log.info(f"Initialized checkpoint store at {self.db_path}")

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_checkpoints (
                    run_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    pipeline_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    total_steps INTEGER NOT NULL,
                    completed_steps INTEGER NOT NULL,
                    environment TEXT DEFAULT 'prod',
                    run_type TEXT DEFAULT 'FULL_REFRESH',
                    params TEXT,  -- JSON
                    metadata TEXT  -- JSON
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS step_checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    duration_seconds REAL,
                    output BLOB,  -- Pickled output
                    error TEXT,
                    attempt INTEGER DEFAULT 1,
                    metadata TEXT,  -- JSON
                    FOREIGN KEY (run_id) REFERENCES pipeline_checkpoints(run_id),
                    UNIQUE(run_id, step_id)
                )
            """)

            # Create indexes for faster queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_checkpoints_status
                ON pipeline_checkpoints(status)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_checkpoints_created
                ON pipeline_checkpoints(created_at)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_steps_run_id
                ON step_checkpoints(run_id)
            """)

            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Get thread-safe database connection."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

    def create_checkpoint(
        self,
        run_id: str,
        source: str,
        pipeline_name: str,
        total_steps: int,
        environment: str = "prod",
        run_type: str = "FULL_REFRESH",
        params: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CheckpointMetadata:
        """Create a new pipeline checkpoint.

        Args:
            run_id: Unique run identifier
            source: Source name (e.g., 'alfabeta')
            pipeline_name: Pipeline name
            total_steps: Total number of steps
            environment: Environment ('dev', 'staging', 'prod')
            run_type: Run type ('FULL_REFRESH', 'DELTA', etc.)
            params: Runtime parameters
            metadata: Additional metadata

        Returns:
            Created checkpoint metadata
        """
        now = datetime.utcnow()

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO pipeline_checkpoints
                (run_id, source, pipeline_name, created_at, updated_at, status,
                 total_steps, completed_steps, environment, run_type, params, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    source,
                    pipeline_name,
                    now.isoformat(),
                    now.isoformat(),
                    "active",
                    total_steps,
                    0,
                    environment,
                    run_type,
                    json.dumps(params or {}),
                    json.dumps(metadata or {}),
                ),
            )
            conn.commit()

        log.info(f"Created checkpoint for run {run_id}")

        return CheckpointMetadata(
            run_id=run_id,
            source=source,
            pipeline_name=pipeline_name,
            created_at=now,
            updated_at=now,
            status="active",
            total_steps=total_steps,
            completed_steps=0,
            environment=environment,
            run_type=run_type,
        )

    def update_checkpoint_status(
        self, run_id: str, status: str, completed_steps: Optional[int] = None
    ) -> None:
        """Update checkpoint status.

        Args:
            run_id: Run identifier
            status: New status ('active', 'completed', 'failed', 'paused')
            completed_steps: Number of completed steps
        """
        with self._get_connection() as conn:
            if completed_steps is not None:
                conn.execute(
                    """
                    UPDATE pipeline_checkpoints
                    SET status = ?, completed_steps = ?, updated_at = ?
                    WHERE run_id = ?
                    """,
                    (status, completed_steps, datetime.utcnow().isoformat(), run_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE pipeline_checkpoints
                    SET status = ?, updated_at = ?
                    WHERE run_id = ?
                    """,
                    (status, datetime.utcnow().isoformat(), run_id),
                )
            conn.commit()

        log.debug(f"Updated checkpoint {run_id} status to {status}")

    def save_step(
        self,
        run_id: str,
        step_id: str,
        status: str,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
        duration_seconds: Optional[float] = None,
        output: Optional[Any] = None,
        error: Optional[str] = None,
        attempt: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Save step checkpoint.

        Args:
            run_id: Run identifier
            step_id: Step identifier
            status: Step status ('pending', 'running', 'completed', 'failed', 'skipped')
            started_at: Step start time
            finished_at: Step finish time
            duration_seconds: Execution duration
            output: Step output (will be pickled)
            error: Error message if failed
            attempt: Attempt number
            metadata: Additional metadata
        """
        # Serialize output
        output_blob = pickle.dumps(output) if output is not None else None

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO step_checkpoints
                (run_id, step_id, status, started_at, finished_at, duration_seconds,
                 output, error, attempt, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    step_id,
                    status,
                    started_at.isoformat() if started_at else None,
                    finished_at.isoformat() if finished_at else None,
                    duration_seconds,
                    output_blob,
                    error,
                    attempt,
                    json.dumps(metadata or {}),
                ),
            )
            conn.commit()

        # Update completed step count
        if status == "completed":
            with self._get_connection() as conn:
                conn.execute(
                    """
                    UPDATE pipeline_checkpoints
                    SET completed_steps = (
                        SELECT COUNT(*) FROM step_checkpoints
                        WHERE run_id = ? AND status = 'completed'
                    ),
                    updated_at = ?
                    WHERE run_id = ?
                    """,
                    (run_id, datetime.utcnow().isoformat(), run_id),
                )
                conn.commit()

        log.debug(f"Saved step checkpoint: {run_id}/{step_id} - {status}")

    def get_checkpoint(self, run_id: str) -> Optional[CheckpointMetadata]:
        """Get checkpoint metadata.

        Args:
            run_id: Run identifier

        Returns:
            Checkpoint metadata or None if not found
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM pipeline_checkpoints WHERE run_id = ?", (run_id,)
            ).fetchone()

        if not row:
            return None

        return CheckpointMetadata(
            run_id=row["run_id"],
            source=row["source"],
            pipeline_name=row["pipeline_name"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            status=row["status"],
            total_steps=row["total_steps"],
            completed_steps=row["completed_steps"],
            environment=row["environment"],
            run_type=row["run_type"],
        )

    def get_step_checkpoints(self, run_id: str) -> List[StepCheckpoint]:
        """Get all step checkpoints for a run.

        Args:
            run_id: Run identifier

        Returns:
            List of step checkpoints
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM step_checkpoints WHERE run_id = ? ORDER BY id",
                (run_id,),
            ).fetchall()

        checkpoints = []
        for row in rows:
            # Deserialize output
            output = None
            if row["output"]:
                try:
                    output = pickle.loads(row["output"])
                except Exception as e:
                    log.warning(f"Failed to deserialize output for {row['step_id']}: {e}")

            checkpoints.append(
                StepCheckpoint(
                    step_id=row["step_id"],
                    status=row["status"],
                    started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
                    finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
                    duration_seconds=row["duration_seconds"],
                    output=output,
                    error=row["error"],
                    attempt=row["attempt"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                )
            )

        return checkpoints

    def get_completed_steps(self, run_id: str) -> List[str]:
        """Get list of completed step IDs.

        Args:
            run_id: Run identifier

        Returns:
            List of completed step IDs
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT step_id FROM step_checkpoints WHERE run_id = ? AND status = 'completed'",
                (run_id,),
            ).fetchall()

        return [row["step_id"] for row in rows]

    def can_resume(self, run_id: str) -> bool:
        """Check if a run can be resumed.

        Args:
            run_id: Run identifier

        Returns:
            True if run can be resumed
        """
        checkpoint = self.get_checkpoint(run_id)
        if not checkpoint:
            return False

        # Can resume if status is active or paused and not all steps completed
        return (
            checkpoint.status in ("active", "paused")
            and checkpoint.completed_steps < checkpoint.total_steps
        )

    def delete_checkpoint(self, run_id: str) -> bool:
        """Delete a checkpoint and all associated step data.

        Args:
            run_id: Run identifier

        Returns:
            True if deleted
        """
        with self._get_connection() as conn:
            # Delete step checkpoints first
            conn.execute("DELETE FROM step_checkpoints WHERE run_id = ?", (run_id,))

            # Delete pipeline checkpoint
            cursor = conn.execute(
                "DELETE FROM pipeline_checkpoints WHERE run_id = ?", (run_id,)
            )
            conn.commit()
            deleted = cursor.rowcount > 0

        if deleted:
            log.info(f"Deleted checkpoint for run {run_id}")

        return deleted

    def cleanup_old_checkpoints(self, max_age_days: int = 30) -> int:
        """Clean up checkpoints older than max_age_days.

        Args:
            max_age_days: Maximum age in days

        Returns:
            Number of checkpoints deleted
        """
        cutoff = datetime.utcnow().timestamp() - (max_age_days * 86400)
        cutoff_iso = datetime.fromtimestamp(cutoff).isoformat()

        with self._get_connection() as conn:
            # Get old run IDs
            rows = conn.execute(
                """
                SELECT run_id FROM pipeline_checkpoints
                WHERE created_at < ? AND status IN ('completed', 'failed')
                """,
                (cutoff_iso,),
            ).fetchall()

            run_ids = [row["run_id"] for row in rows]

            # Delete step checkpoints
            conn.execute(
                "DELETE FROM step_checkpoints WHERE run_id IN ({})".format(
                    ",".join("?" * len(run_ids))
                ),
                run_ids,
            )

            # Delete pipeline checkpoints
            cursor = conn.execute(
                "DELETE FROM pipeline_checkpoints WHERE run_id IN ({})".format(
                    ",".join("?" * len(run_ids))
                ),
                run_ids,
            )

            conn.commit()
            count = cursor.rowcount

        if count > 0:
            log.info(f"Cleaned up {count} old checkpoints")

        return count

    def list_active_checkpoints(self) -> List[CheckpointMetadata]:
        """List all active checkpoints.

        Returns:
            List of active checkpoint metadata
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM pipeline_checkpoints
                WHERE status IN ('active', 'paused')
                ORDER BY created_at DESC
                """
            ).fetchall()

        return [
            CheckpointMetadata(
                run_id=row["run_id"],
                source=row["source"],
                pipeline_name=row["pipeline_name"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                status=row["status"],
                total_steps=row["total_steps"],
                completed_steps=row["completed_steps"],
                environment=row["environment"],
                run_type=row["run_type"],
            )
            for row in rows
        ]


# Global checkpoint store singleton
_checkpoint_store: Optional[CheckpointStore] = None


def get_checkpoint_store(db_path: Optional[str] = None) -> CheckpointStore:
    """Get global checkpoint store singleton.

    Args:
        db_path: Optional database path (only used on first call)

    Returns:
        Checkpoint store instance
    """
    global _checkpoint_store
    if _checkpoint_store is None:
        _checkpoint_store = CheckpointStore(db_path)
    return _checkpoint_store
