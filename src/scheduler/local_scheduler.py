"""
Local in-process scheduler for desktop app.

Replaces distributed DAG scheduler with FIFO/priority queue.
"""

import logging
import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from threading import Thread, Event, RLock
from queue import PriorityQueue, Empty
import time

logger = logging.getLogger(__name__)


class JobPriority(int, Enum):
    """Job priority levels."""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0


class JobState(str, Enum):
    """Job state in queue."""
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class QueuedJob:
    """Job in scheduler queue."""
    job_id: str
    pipeline_id: str
    source: str
    priority: JobPriority
    config: Dict[str, Any]
    queued_at: datetime
    state: JobState = JobState.QUEUED
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 0

    def __lt__(self, other):
        """Compare by priority for PriorityQueue."""
        return self.priority.value < other.priority.value


class LocalScheduler:
    """
    Local in-process job scheduler.

    Features:
    - FIFO/priority queue
    - SQLite persistence
    - Resume unfinished jobs on startup
    - Thread-safe
    """

    def __init__(
        self,
        db_path: Path,
        executor: Callable[[QueuedJob], None],
        max_concurrent: int = 1
    ):
        """
        Initialize local scheduler.

        Args:
            db_path: Path to SQLite database
            executor: Function to execute jobs
            max_concurrent: Max concurrent jobs
        """
        self.db_path = db_path
        self.executor = executor
        self.max_concurrent = max_concurrent

        self._queue: PriorityQueue = PriorityQueue()
        self._jobs: Dict[str, QueuedJob] = {}
        self._lock = RLock()
        self._running = False
        self._stop_event = Event()
        self._worker_threads: List[Thread] = []

        self._init_db()
        self._load_pending_jobs()

    def _init_db(self):
        """Initialize SQLite database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS queued_jobs (
                    job_id TEXT PRIMARY KEY,
                    pipeline_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    config TEXT NOT NULL,
                    queued_at TEXT NOT NULL,
                    state TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    error TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 0
                )
            """)
            conn.commit()

        logger.info(f"Initialized scheduler database: {self.db_path}")

    def _save_job(self, job: QueuedJob):
        """Save job to database."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO queued_jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.job_id,
                job.pipeline_id,
                job.source,
                job.priority.value,
                json.dumps(job.config),
                job.queued_at.isoformat(),
                job.state.value,
                job.started_at.isoformat() if job.started_at else None,
                job.finished_at.isoformat() if job.finished_at else None,
                job.error,
                job.retry_count,
                job.max_retries
            ))
            conn.commit()

    def _load_pending_jobs(self):
        """Load pending jobs from database on startup."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("""
                SELECT * FROM queued_jobs
                WHERE state IN ('queued', 'running', 'paused')
                ORDER BY priority ASC, queued_at ASC
            """)

            count = 0
            for row in cursor.fetchall():
                job = QueuedJob(
                    job_id=row[0],
                    pipeline_id=row[1],
                    source=row[2],
                    priority=JobPriority(row[3]),
                    config=json.loads(row[4]),
                    queued_at=datetime.fromisoformat(row[5]),
                    state=JobState(row[6]),
                    started_at=datetime.fromisoformat(row[7]) if row[7] else None,
                    finished_at=datetime.fromisoformat(row[8]) if row[8] else None,
                    error=row[9],
                    retry_count=row[10],
                    max_retries=row[11]
                )

                # Re-queue interrupted jobs
                if job.state == JobState.RUNNING:
                    job.state = JobState.QUEUED
                    job.started_at = None

                self._jobs[job.job_id] = job
                self._queue.put(job)
                count += 1

        logger.info(f"Loaded {count} pending jobs from database")

    def queue_job(
        self,
        job_id: str,
        pipeline_id: str,
        source: str,
        config: Dict[str, Any],
        priority: JobPriority = JobPriority.NORMAL,
        max_retries: int = 0
    ):
        """
        Queue job for execution.

        Args:
            job_id: Unique job identifier
            pipeline_id: Pipeline to execute
            source: Data source
            config: Job configuration
            priority: Job priority
            max_retries: Max retry attempts
        """
        with self._lock:
            if job_id in self._jobs:
                logger.warning(f"Job already queued: {job_id}")
                return

            job = QueuedJob(
                job_id=job_id,
                pipeline_id=pipeline_id,
                source=source,
                priority=priority,
                config=config,
                queued_at=datetime.utcnow(),
                max_retries=max_retries
            )

            self._jobs[job_id] = job
            self._queue.put(job)
            self._save_job(job)

            logger.info(f"Queued job: {job_id} (priority={priority.name})")

    def start(self):
        """Start scheduler workers."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._stop_event.clear()

        # Start worker threads
        for i in range(self.max_concurrent):
            thread = Thread(target=self._worker_loop, daemon=True, name=f"scheduler-worker-{i}")
            thread.start()
            self._worker_threads.append(thread)

        logger.info(f"Started {self.max_concurrent} scheduler workers")

    def stop(self, timeout: float = 10.0):
        """
        Stop scheduler.

        Args:
            timeout: Max time to wait for workers
        """
        if not self._running:
            return

        logger.info("Stopping scheduler...")
        self._running = False
        self._stop_event.set()

        # Wait for workers
        for thread in self._worker_threads:
            thread.join(timeout=timeout)

        self._worker_threads.clear()
        logger.info("Scheduler stopped")

    def _worker_loop(self):
        """Worker thread loop."""
        while self._running and not self._stop_event.is_set():
            try:
                # Get next job (1 second timeout)
                job = self._queue.get(timeout=1.0)

                # Execute job
                self._execute_job(job)

            except Empty:
                continue
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)

    def _execute_job(self, job: QueuedJob):
        """Execute job."""
        try:
            # Update state
            with self._lock:
                job.state = JobState.RUNNING
                job.started_at = datetime.utcnow()
                self._save_job(job)

            logger.info(f"Executing job: {job.job_id}")

            # Execute via callback
            self.executor(job)

            # Mark completed
            with self._lock:
                job.state = JobState.COMPLETED
                job.finished_at = datetime.utcnow()
                self._save_job(job)

            logger.info(f"Job completed: {job.job_id}")

        except Exception as e:
            logger.error(f"Job failed: {job.job_id} - {e}", exc_info=True)

            with self._lock:
                job.error = str(e)
                job.retry_count += 1

                # Retry if allowed
                if job.retry_count < job.max_retries:
                    job.state = JobState.QUEUED
                    job.started_at = None
                    job.error = None
                    self._queue.put(job)
                    logger.info(f"Retrying job: {job.job_id} (attempt {job.retry_count + 1}/{job.max_retries})")
                else:
                    job.state = JobState.FAILED
                    job.finished_at = datetime.utcnow()

                self._save_job(job)

    def get_job(self, job_id: str) -> Optional[QueuedJob]:
        """Get job by ID."""
        with self._lock:
            return self._jobs.get(job_id)

    def get_all_jobs(self) -> List[QueuedJob]:
        """Get all jobs."""
        with self._lock:
            return list(self._jobs.values())

    def get_queue_size(self) -> int:
        """Get number of queued jobs."""
        return self._queue.qsize()

    def pause_job(self, job_id: str):
        """Pause job (if supported by executor)."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job.state == JobState.RUNNING:
                job.state = JobState.PAUSED
                self._save_job(job)
                logger.info(f"Job paused: {job_id}")

    def resume_job(self, job_id: str):
        """Resume paused job."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job.state == JobState.PAUSED:
                job.state = JobState.QUEUED
                self._queue.put(job)
                self._save_job(job)
                logger.info(f"Job resumed: {job_id}")

    def cancel_job(self, job_id: str):
        """Cancel job."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.state = JobState.STOPPED
                job.finished_at = datetime.utcnow()
                self._save_job(job)
                logger.info(f"Job cancelled: {job_id}")

    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        with self._lock:
            by_state = {}
            for state in JobState:
                by_state[state.value] = len([j for j in self._jobs.values() if j.state == state])

            return {
                'total_jobs': len(self._jobs),
                'queue_size': self.get_queue_size(),
                'by_state': by_state,
                'is_running': self._running,
                'max_concurrent': self.max_concurrent
            }
