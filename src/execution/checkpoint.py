"""
Checkpoint manager for execution state persistence.
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Manage execution checkpoints for crash recovery.

    Checkpoints are persisted to SQLite for crash recovery and resume support.
    """

    def __init__(self, db_path: Path):
        """
        Initialize checkpoint manager.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize checkpoint database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    run_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    checkpoint_data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (run_id, step_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS execution_state (
                    run_id TEXT PRIMARY KEY,
                    pipeline_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    run_type TEXT NOT NULL,
                    environment TEXT NOT NULL,
                    state TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    progress REAL DEFAULT 0.0,
                    current_step TEXT,
                    total_steps INTEGER DEFAULT 0,
                    completed_steps INTEGER DEFAULT 0,
                    error TEXT,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_checkpoints_run_id
                ON checkpoints(run_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_execution_state_state
                ON execution_state(state)
            """)

    def save_checkpoint(
        self,
        run_id: str,
        step_id: str,
        data: Dict[str, Any]
    ):
        """
        Save checkpoint for execution step.

        Args:
            run_id: Run identifier
            step_id: Step identifier
            data: Checkpoint data to save
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO checkpoints (run_id, step_id, checkpoint_data, created_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    run_id,
                    step_id,
                    json.dumps(data),
                    datetime.utcnow().isoformat()
                ))
            logger.debug(f"Checkpoint saved: {run_id}/{step_id}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint {run_id}/{step_id}: {e}")

    def load_checkpoint(self, run_id: str, step_id: str) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint for execution step.

        Args:
            run_id: Run identifier
            step_id: Step identifier

        Returns:
            Checkpoint data or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT checkpoint_data FROM checkpoints
                    WHERE run_id = ? AND step_id = ?
                """, (run_id, step_id))
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
        except Exception as e:
            logger.error(f"Failed to load checkpoint {run_id}/{step_id}: {e}")
        return None

    def list_checkpoints(self, run_id: str) -> List[str]:
        """
        List all checkpoint step IDs for a run.

        Args:
            run_id: Run identifier

        Returns:
            List of step IDs with checkpoints
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT step_id FROM checkpoints
                    WHERE run_id = ?
                    ORDER BY created_at
                """, (run_id,))
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to list checkpoints for {run_id}: {e}")
            return []

    def save_execution_state(
        self,
        run_id: str,
        pipeline_id: str,
        source: str,
        run_type: str,
        environment: str,
        state: str,
        started_at: datetime,
        finished_at: Optional[datetime] = None,
        progress: float = 0.0,
        current_step: Optional[str] = None,
        total_steps: int = 0,
        completed_steps: int = 0,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Save complete execution state"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO execution_state
                    (run_id, pipeline_id, source, run_type, environment, state,
                     started_at, finished_at, progress, current_step,
                     total_steps, completed_steps, error, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_id, pipeline_id, source, run_type, environment, state,
                    started_at.isoformat(),
                    finished_at.isoformat() if finished_at else None,
                    progress, current_step, total_steps, completed_steps, error,
                    json.dumps(metadata) if metadata else None
                ))
            logger.debug(f"Execution state saved: {run_id}")
        except Exception as e:
            logger.error(f"Failed to save execution state {run_id}: {e}")

    def load_execution_state(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Load complete execution state"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT pipeline_id, source, run_type, environment, state,
                           started_at, finished_at, progress, current_step,
                           total_steps, completed_steps, error, metadata
                    FROM execution_state
                    WHERE run_id = ?
                """, (run_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        'pipeline_id': row[0],
                        'source': row[1],
                        'run_type': row[2],
                        'environment': row[3],
                        'state': row[4],
                        'started_at': row[5],
                        'finished_at': row[6],
                        'progress': row[7],
                        'current_step': row[8],
                        'total_steps': row[9],
                        'completed_steps': row[10],
                        'error': row[11],
                        'metadata': json.loads(row[12]) if row[12] else None
                    }
        except Exception as e:
            logger.error(f"Failed to load execution state {run_id}: {e}")
        return None

    def list_resumable_executions(self) -> List[str]:
        """List executions that can be resumed"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT DISTINCT e.run_id
                    FROM execution_state e
                    INNER JOIN checkpoints c ON e.run_id = c.run_id
                    WHERE e.state IN ('paused', 'failed', 'crashed')
                    ORDER BY e.started_at DESC
                """)
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to list resumable executions: {e}")
            return []

    def delete_checkpoints(self, run_id: str):
        """Delete all checkpoints for a run"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM checkpoints WHERE run_id = ?", (run_id,))
                conn.execute("DELETE FROM execution_state WHERE run_id = ?", (run_id,))
            logger.info(f"Checkpoints deleted: {run_id}")
        except Exception as e:
            logger.error(f"Failed to delete checkpoints {run_id}: {e}")

    def cleanup_old_checkpoints(self, days: int = 30):
        """Delete checkpoints older than specified days"""
        try:
            cutoff = datetime.utcnow().isoformat()[:10]  # YYYY-MM-DD
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM checkpoints
                    WHERE created_at < date(?, '-' || ? || ' days')
                """, (cutoff, days))
                deleted = cursor.rowcount
                if deleted > 0:
                    logger.info(f"Cleaned up {deleted} old checkpoints")
        except Exception as e:
            logger.error(f"Failed to cleanup old checkpoints: {e}")
