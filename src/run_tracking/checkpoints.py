"""
Checkpoint system for crash recovery.

Saves step-level progress to resume after crashes.
"""

import logging
import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Checkpoint:
    """Step-level checkpoint."""
    job_id: str
    step_id: str
    step_index: int
    timestamp: datetime
    data: Dict[str, Any]
    status: str  # 'completed', 'failed', 'skipped'


class CheckpointManager:
    """
    Manages execution checkpoints for crash recovery.

    Features:
    - Step-level progress tracking
    - Resume from last successful step
    - Cleanup completed jobs
    """

    def __init__(self, db_path: Path):
        """
        Initialize checkpoint manager.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._conn = None
        self._init_db()

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def _init_db(self):
        """Initialize database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(str(self.db_path)) as conn:
            # Checkpoints table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    job_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    data TEXT NOT NULL,
                    status TEXT NOT NULL,
                    PRIMARY KEY (job_id, step_id)
                )
            """)

            # Job metadata table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS job_metadata (
                    job_id TEXT PRIMARY KEY,
                    pipeline_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    last_checkpoint_at TEXT,
                    total_steps INTEGER,
                    completed_steps INTEGER DEFAULT 0,
                    state TEXT NOT NULL,
                    config TEXT
                )
            """)

            conn.commit()

        logger.info(f"Initialized checkpoint database: {self.db_path}")

    def save_checkpoint(
        self,
        job_id: str,
        step_id: str,
        step_index: int,
        data: Dict[str, Any],
        status: str = 'completed'
    ):
        """
        Save step checkpoint.

        Args:
            job_id: Job identifier
            step_id: Step identifier
            step_index: Step index in pipeline
            data: Step output data
            status: Step status
        """
        checkpoint = Checkpoint(
            job_id=job_id,
            step_id=step_id,
            step_index=step_index,
            timestamp=datetime.utcnow(),
            data=data,
            status=status
        )

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO checkpoints VALUES (?, ?, ?, ?, ?, ?)
            """, (
                checkpoint.job_id,
                checkpoint.step_id,
                checkpoint.step_index,
                checkpoint.timestamp.isoformat(),
                json.dumps(checkpoint.data),
                checkpoint.status
            ))

            # Update job metadata
            conn.execute("""
                UPDATE job_metadata
                SET last_checkpoint_at = ?,
                    completed_steps = (
                        SELECT COUNT(*) FROM checkpoints
                        WHERE job_id = ? AND status = 'completed'
                    )
                WHERE job_id = ?
            """, (
                checkpoint.timestamp.isoformat(),
                job_id,
                job_id
            ))

            conn.commit()

        logger.debug(f"Checkpoint saved: {job_id} / {step_id}")

    def init_job(
        self,
        job_id: str,
        pipeline_id: str,
        source: str,
        total_steps: int,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize job for checkpointing.

        Args:
            job_id: Job identifier
            pipeline_id: Pipeline identifier
            source: Data source
            total_steps: Total number of steps
            config: Job configuration
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO job_metadata VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                pipeline_id,
                source,
                datetime.utcnow().isoformat(),
                None,
                total_steps,
                0,
                'running',
                json.dumps(config) if config else None
            ))
            conn.commit()

        logger.info(f"Job initialized: {job_id} ({total_steps} steps)")

    def mark_job_completed(self, job_id: str):
        """Mark job as completed."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                UPDATE job_metadata SET state = 'completed' WHERE job_id = ?
            """, (job_id,))
            conn.commit()

        logger.info(f"Job completed: {job_id}")

    def mark_job_failed(self, job_id: str, error: Optional[str] = None):
        """Mark job as failed."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                UPDATE job_metadata SET state = 'failed' WHERE job_id = ?
            """, (job_id,))
            conn.commit()

        logger.info(f"Job failed: {job_id}")

    def get_job_checkpoints(self, job_id: str) -> List[Checkpoint]:
        """
        Get all checkpoints for job.

        Args:
            job_id: Job identifier

        Returns:
            List of checkpoints sorted by step_index
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("""
                SELECT * FROM checkpoints
                WHERE job_id = ?
                ORDER BY step_index ASC
            """, (job_id,))

            checkpoints = []
            for row in cursor.fetchall():
                checkpoint = Checkpoint(
                    job_id=row[0],
                    step_id=row[1],
                    step_index=row[2],
                    timestamp=datetime.fromisoformat(row[3]),
                    data=json.loads(row[4]),
                    status=row[5]
                )
                checkpoints.append(checkpoint)

            return checkpoints

    def get_last_checkpoint(self, job_id: str) -> Optional[Checkpoint]:
        """Get last checkpoint for job."""
        checkpoints = self.get_job_checkpoints(job_id)
        return checkpoints[-1] if checkpoints else None

    def get_completed_steps(self, job_id: str) -> List[str]:
        """Get list of completed step IDs."""
        checkpoints = self.get_job_checkpoints(job_id)
        return [cp.step_id for cp in checkpoints if cp.status == 'completed']

    def list_resumable_jobs(self) -> List[Dict[str, Any]]:
        """
        List jobs that can be resumed.

        Returns:
            List of job metadata dicts
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("""
                SELECT * FROM job_metadata
                WHERE state = 'running'
                ORDER BY started_at DESC
            """)

            jobs = []
            for row in cursor.fetchall():
                jobs.append({
                    'job_id': row[0],
                    'pipeline_id': row[1],
                    'source': row[2],
                    'started_at': row[3],
                    'last_checkpoint_at': row[4],
                    'total_steps': row[5],
                    'completed_steps': row[6],
                    'state': row[7],
                    'config': json.loads(row[8]) if row[8] else None
                })

            return jobs

    def cleanup_job(self, job_id: str):
        """
        Cleanup checkpoints for completed job.

        Args:
            job_id: Job identifier
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("DELETE FROM checkpoints WHERE job_id = ?", (job_id,))
            conn.execute("DELETE FROM job_metadata WHERE job_id = ?", (job_id,))
            conn.commit()

        logger.info(f"Job cleaned up: {job_id}")

    def cleanup_old_jobs(self, keep_days: int = 7):
        """
        Cleanup jobs older than N days.

        Args:
            keep_days: Days to keep
        """
        cutoff = datetime.utcnow().timestamp() - (keep_days * 86400)
        cutoff_iso = datetime.fromtimestamp(cutoff).isoformat()

        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("""
                SELECT job_id FROM job_metadata
                WHERE started_at < ? AND state IN ('completed', 'failed')
            """, (cutoff_iso,))

            job_ids = [row[0] for row in cursor.fetchall()]

            for job_id in job_ids:
                conn.execute("DELETE FROM checkpoints WHERE job_id = ?", (job_id,))
                conn.execute("DELETE FROM job_metadata WHERE job_id = ?", (job_id,))

            conn.commit()

        logger.info(f"Cleaned up {len(job_ids)} old jobs")

    def get_stats(self) -> Dict[str, Any]:
        """Get checkpoint statistics."""
        with sqlite3.connect(str(self.db_path)) as conn:
            # Total jobs
            cursor = conn.execute("SELECT COUNT(*) FROM job_metadata")
            total_jobs = cursor.fetchone()[0]

            # By state
            cursor = conn.execute("""
                SELECT state, COUNT(*) FROM job_metadata GROUP BY state
            """)
            by_state = {row[0]: row[1] for row in cursor.fetchall()}

            # Total checkpoints
            cursor = conn.execute("SELECT COUNT(*) FROM checkpoints")
            total_checkpoints = cursor.fetchone()[0]

            return {
                'total_jobs': total_jobs,
                'by_state': by_state,
                'total_checkpoints': total_checkpoints,
                'resumable_jobs': len(self.list_resumable_jobs())
            }
