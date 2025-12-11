"""
Job management for desktop UI.

Uses multiprocessing to allow hard-stopping running jobs on Windows.
Each job runs `run_pipeline` in a separate process; status is polled via a
Queue to avoid blocking the UI thread.
"""

from __future__ import annotations

import multiprocessing as mp
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from src.entrypoints.run_pipeline import run_pipeline


@dataclass
class JobInfo:
    job_id: str
    source: str
    run_type: str
    environment: str
    status: str = "pending"  # pending, running, completed, stopped, failed
    process: Optional[mp.Process] = None
    queue: Optional[mp.Queue] = None
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    result: Optional[dict] = None


class JobManager:
    """Simple process-based job manager for UI."""

    def __init__(self) -> None:
        mp.set_start_method("spawn", force=True)
        self.jobs: Dict[str, JobInfo] = {}

    def start_job(self, job_id: str, *, source: str, run_type: str, environment: str) -> None:
        if job_id in self.jobs and self.jobs[job_id].status == "running":
            return

        q: mp.Queue = mp.Queue()
        proc = mp.Process(target=_job_worker, args=(q, source, run_type, environment), daemon=True)
        info = JobInfo(
            job_id=job_id,
            source=source,
            run_type=run_type,
            environment=environment,
            status="running",
            process=proc,
            queue=q,
            started_at=time.time(),
        )
        self.jobs[job_id] = info
        proc.start()

    def stop_job(self, job_id: str) -> None:
        info = self.jobs.get(job_id)
        if not info or not info.process:
            return
        if info.process.is_alive():
            info.process.terminate()
            info.process.join(timeout=2)
        info.status = "stopped"
        info.ended_at = time.time()

    def poll(self) -> None:
        """Poll job queues for results and update statuses."""
        for info in list(self.jobs.values()):
            if info.queue:
                while not info.queue.empty():
                    result = info.queue.get()
                    info.result = result
                    info.status = result.get("status", "completed")
                    info.ended_at = time.time()
            if info.process and not info.process.is_alive() and info.status == "running":
                # Process exited without sending result
                info.status = "completed"
                info.ended_at = time.time()

    def get_status(self, job_id: str) -> Optional[str]:
        info = self.jobs.get(job_id)
        return info.status if info else None

    def list_jobs(self) -> Dict[str, JobInfo]:
        self.poll()
        return self.jobs


def _job_worker(queue: mp.Queue, source: str, run_type: str, environment: str) -> None:
    try:
        result = run_pipeline(source=source, run_type=run_type, environment=environment)
    except Exception as exc:  # pragma: no cover - defensive
        result = {"status": "failed", "error": str(exc)}
    queue.put(result or {"status": "completed"})

