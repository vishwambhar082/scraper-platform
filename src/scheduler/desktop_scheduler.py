"""
Desktop-native scheduler (Airflow replacement).
"""

import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
import threading
import time
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class ScheduledJob:
    """Scheduled job definition"""
    job_id: str
    pipeline_id: str
    source: str
    schedule_type: str  # 'once', 'interval', 'cron', 'manual'
    schedule_config: Dict[str, Any]
    next_run: datetime
    enabled: bool = True
    last_run: Optional[datetime] = None
    run_count: int = 0
    created_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'job_id': self.job_id,
            'pipeline_id': self.pipeline_id,
            'source': self.source,
            'schedule_type': self.schedule_type,
            'schedule_config': self.schedule_config,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'enabled': self.enabled,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'run_count': self.run_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'metadata': self.metadata
        }


class DesktopScheduler:
    """
    Desktop-native scheduler (Airflow replacement).

    Features:
    - SQLite-backed persistent queue
    - Survives app restarts
    - Simple interval/cron scheduling
    - No external dependencies
    - Thread-safe operations
    """

    def __init__(self, db_path: Path, execution_engine):
        """
        Initialize desktop scheduler.

        Args:
            db_path: Path to SQLite database
            execution_engine: CoreExecutionEngine instance
        """
        self.db_path = db_path
        self.execution_engine = execution_engine
        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize scheduler database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_jobs (
                    job_id TEXT PRIMARY KEY,
                    pipeline_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    schedule_type TEXT NOT NULL,
                    schedule_config TEXT NOT NULL,
                    next_run TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    last_run TEXT,
                    run_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS job_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT,
                    error TEXT,
                    FOREIGN KEY (job_id) REFERENCES scheduled_jobs(job_id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_job_history_job_id
                ON job_history(job_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_next_run
                ON scheduled_jobs(next_run, enabled)
            """)

    def schedule_job(
        self,
        job_id: str,
        pipeline_id: str,
        source: str,
        schedule_type: str,
        schedule_config: Dict[str, Any],
        enabled: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add or update job schedule.

        Args:
            job_id: Unique job identifier
            pipeline_id: Pipeline to execute
            source: Data source name
            schedule_type: 'once', 'interval', 'cron', 'manual'
            schedule_config: Schedule configuration dict
            enabled: Whether job is enabled
            metadata: Additional metadata

        Returns:
            True if scheduled successfully
        """
        try:
            next_run = self._calculate_next_run(schedule_type, schedule_config)

            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO scheduled_jobs
                    (job_id, pipeline_id, source, schedule_type, schedule_config,
                     next_run, enabled, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job_id,
                    pipeline_id,
                    source,
                    schedule_type,
                    json.dumps(schedule_config),
                    next_run.isoformat(),
                    1 if enabled else 0,
                    datetime.utcnow().isoformat(),
                    json.dumps(metadata) if metadata else None
                ))

            logger.info(f"Scheduled job: {job_id} (next run: {next_run})")
            return True

        except Exception as e:
            logger.error(f"Failed to schedule job {job_id}: {e}")
            return False

    def unschedule_job(self, job_id: str) -> bool:
        """Remove job from schedule"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM scheduled_jobs WHERE job_id = ?", (job_id,))
            logger.info(f"Unscheduled job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to unschedule job {job_id}: {e}")
            return False

    def enable_job(self, job_id: str) -> bool:
        """Enable scheduled job"""
        return self._set_job_enabled(job_id, True)

    def disable_job(self, job_id: str) -> bool:
        """Disable scheduled job"""
        return self._set_job_enabled(job_id, False)

    def _set_job_enabled(self, job_id: str, enabled: bool) -> bool:
        """Set job enabled status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE scheduled_jobs SET enabled = ? WHERE job_id = ?",
                    (1 if enabled else 0, job_id)
                )
            logger.info(f"Job {job_id} {'enabled' if enabled else 'disabled'}")
            return True
        except Exception as e:
            logger.error(f"Failed to set job {job_id} enabled={enabled}: {e}")
            return False

    def get_scheduled_jobs(self, enabled_only: bool = False) -> List[ScheduledJob]:
        """Get all scheduled jobs"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT * FROM scheduled_jobs"
                if enabled_only:
                    query += " WHERE enabled = 1"
                query += " ORDER BY next_run"

                cursor = conn.execute(query)
                jobs = []
                for row in cursor.fetchall():
                    jobs.append(self._row_to_job(row))
                return jobs
        except Exception as e:
            logger.error(f"Failed to get scheduled jobs: {e}")
            return []

    def get_due_jobs(self) -> List[ScheduledJob]:
        """Get jobs that are due to run"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT * FROM scheduled_jobs
                    WHERE enabled = 1 AND next_run <= ?
                    ORDER BY next_run
                """, (datetime.utcnow().isoformat(),))

                jobs = []
                for row in cursor.fetchall():
                    jobs.append(self._row_to_job(row))
                return jobs
        except Exception as e:
            logger.error(f"Failed to get due jobs: {e}")
            return []

    def _row_to_job(self, row) -> ScheduledJob:
        """Convert database row to ScheduledJob"""
        return ScheduledJob(
            job_id=row[0],
            pipeline_id=row[1],
            source=row[2],
            schedule_type=row[3],
            schedule_config=json.loads(row[4]),
            next_run=datetime.fromisoformat(row[5]),
            enabled=bool(row[6]),
            last_run=datetime.fromisoformat(row[7]) if row[7] else None,
            run_count=row[8],
            created_at=datetime.fromisoformat(row[9]) if row[9] else None,
            metadata=json.loads(row[10]) if row[10] else None
        )

    def _calculate_next_run(
        self,
        schedule_type: str,
        config: Dict[str, Any],
        from_time: Optional[datetime] = None
    ) -> datetime:
        """Calculate next run time based on schedule configuration"""
        if from_time is None:
            from_time = datetime.utcnow()

        if schedule_type == 'once':
            # Run once at specified time
            run_at = config.get('run_at')
            if isinstance(run_at, str):
                return datetime.fromisoformat(run_at)
            return run_at or from_time

        elif schedule_type == 'interval':
            # Run every N minutes/hours/days
            minutes = config.get('interval_minutes')
            hours = config.get('interval_hours')
            days = config.get('interval_days')

            delta = timedelta(
                minutes=minutes or 0,
                hours=hours or 0,
                days=days or 0
            )
            return from_time + delta

        elif schedule_type == 'cron':
            # Simple cron: run at specific hour/minute daily
            hour = config.get('hour', 0)
            minute = config.get('minute', 0)
            day_of_week = config.get('day_of_week')  # 0-6, Monday=0

            next_run = from_time.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # If time already passed today, move to tomorrow
            if next_run <= from_time:
                next_run += timedelta(days=1)

            # Handle day of week
            if day_of_week is not None:
                while next_run.weekday() != day_of_week:
                    next_run += timedelta(days=1)

            return next_run

        elif schedule_type == 'manual':
            # Manual runs only, return far future
            return datetime.max

        else:
            logger.warning(f"Unknown schedule type: {schedule_type}, defaulting to manual")
            return datetime.max

    def start(self):
        """Start scheduler"""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name="DesktopScheduler"
        )
        self._scheduler_thread.start()
        logger.info("DesktopScheduler started")

    def stop(self):
        """Stop scheduler"""
        if not self._running:
            return

        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        logger.info("DesktopScheduler stopped")

    def _scheduler_loop(self):
        """Main scheduler loop"""
        logger.info("DesktopScheduler loop started")

        while self._running:
            try:
                # Check for due jobs every 10 seconds
                due_jobs = self.get_due_jobs()

                for job in due_jobs:
                    self._execute_job(job)

                # Sleep before next check
                time.sleep(10)

            except Exception as e:
                logger.error(f"Scheduler loop error: {e}", exc_info=True)
                time.sleep(30)  # Back off on error

        logger.info("DesktopScheduler loop stopped")

    def _execute_job(self, job: ScheduledJob):
        """Execute scheduled job"""
        run_id = f"{job.job_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        try:
            logger.info(f"Executing scheduled job: {job.job_id} (run_id: {run_id})")

            # Start execution via core engine
            self.execution_engine.start_execution(
                run_id=run_id,
                pipeline_id=job.pipeline_id,
                source=job.source,
                run_type=job.schedule_config.get('run_type', 'FULL_REFRESH'),
                environment=job.schedule_config.get('environment', 'dev'),
                metadata={
                    'scheduled': True,
                    'schedule_type': job.schedule_type,
                    'job_id': job.job_id
                }
            )

            # Calculate next run
            next_run = self._calculate_next_run(
                job.schedule_type,
                job.schedule_config,
                from_time=datetime.utcnow()
            )

            # Update job record
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE scheduled_jobs
                    SET last_run = ?, run_count = run_count + 1, next_run = ?
                    WHERE job_id = ?
                """, (datetime.utcnow().isoformat(), next_run.isoformat(), job.job_id))

                # Record in history
                conn.execute("""
                    INSERT INTO job_history (job_id, run_id, started_at, status)
                    VALUES (?, ?, ?, ?)
                """, (job.job_id, run_id, datetime.utcnow().isoformat(), 'started'))

            logger.info(f"Scheduled job executed: {job.job_id} (next run: {next_run})")

        except Exception as e:
            logger.error(f"Failed to execute job {job.job_id}: {e}", exc_info=True)

            # Record failure in history
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO job_history (job_id, run_id, started_at, status, error)
                        VALUES (?, ?, ?, ?, ?)
                    """, (job.job_id, run_id, datetime.utcnow().isoformat(), 'failed', str(e)))
            except:
                pass

    def get_job_history(self, job_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get execution history for a job"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT run_id, started_at, finished_at, status, error
                    FROM job_history
                    WHERE job_id = ?
                    ORDER BY started_at DESC
                    LIMIT ?
                """, (job_id, limit))

                history = []
                for row in cursor.fetchall():
                    history.append({
                        'run_id': row[0],
                        'started_at': row[1],
                        'finished_at': row[2],
                        'status': row[3],
                        'error': row[4]
                    })
                return history
        except Exception as e:
            logger.error(f"Failed to get job history for {job_id}: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM scheduled_jobs")
                total_jobs = cursor.fetchone()[0]

                cursor = conn.execute("SELECT COUNT(*) FROM scheduled_jobs WHERE enabled = 1")
                enabled_jobs = cursor.fetchone()[0]

                cursor = conn.execute("""
                    SELECT COUNT(*) FROM scheduled_jobs
                    WHERE enabled = 1 AND next_run <= ?
                """, (datetime.utcnow().isoformat(),))
                due_jobs = cursor.fetchone()[0]

                cursor = conn.execute("SELECT COUNT(*) FROM job_history")
                total_runs = cursor.fetchone()[0]

                return {
                    'total_jobs': total_jobs,
                    'enabled_jobs': enabled_jobs,
                    'due_jobs': due_jobs,
                    'total_runs': total_runs,
                    'is_running': self._running
                }
        except Exception as e:
            logger.error(f"Failed to get scheduler stats: {e}")
            return {}
