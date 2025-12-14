# Desktop Application - Critical Path Roadmap

**Current State:** 55% Complete (82.5/150 points)
**Target:** 90% Production-Ready Desktop Application
**Timeline:** 12-16 weeks
**Priority:** Execution stability → User control → Developer experience

---

## 🎯 Executive Summary

Based on your comprehensive gap analysis, here's the **critical path** to transform your platform from a "backend with UI" to a **true desktop application**.

### Critical Insight
Your biggest gaps are **architectural**, not features:
1. No single execution engine (multiple runners without coordination)
2. UI is a viewer, not a control plane (polling, not commanding)
3. Airflow dependency contradicts desktop goals

---

## 🔴 PHASE 1: EXECUTION FOUNDATION (Weeks 1-4)

**Goal:** Single authoritative execution engine that owns all job lifecycle

### 1.1 Unified Execution Engine ⚡ CRITICAL

**Current Problem:**
- Multiple runners (`runner.py`, `runner_enhanced.py`, `JobManager`)
- No single source of truth for execution state
- Cancellation doesn't propagate properly

**Implementation:**

Create `src/execution/core_engine.py`:

```python
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Any
from enum import Enum
import threading
import logging
from datetime import datetime
from queue import Queue, Empty
import signal

logger = logging.getLogger(__name__)

class ExecutionState(Enum):
    """Execution lifecycle states"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"
    CRASHED = "crashed"

@dataclass
class ExecutionContext:
    """Single source of truth for execution"""
    run_id: str
    state: ExecutionState
    pipeline_id: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    current_step: Optional[str] = None
    progress: float = 0.0
    error: Optional[str] = None

    # Control signals
    pause_signal: threading.Event = field(default_factory=threading.Event)
    stop_signal: threading.Event = field(default_factory=threading.Event)
    resume_signal: threading.Event = field(default_factory=threading.Event)

    # Checkpointing
    completed_steps: set = field(default_factory=set)
    checkpoint_data: Dict[str, Any] = field(default_factory=dict)

class CoreExecutionEngine:
    """
    Single authoritative execution engine.

    Responsibilities:
    - Owns all execution state
    - Propagates control signals (pause/stop/resume)
    - Manages checkpoints
    - Coordinates with UI via callbacks
    """

    def __init__(self):
        self._executions: Dict[str, ExecutionContext] = {}
        self._lock = threading.RLock()
        self._event_callbacks: list = []
        self._executor_thread: Optional[threading.Thread] = None
        self._running = False
        self._command_queue = Queue()

    def start_execution(self, run_id: str, pipeline_id: str) -> ExecutionContext:
        """Start new execution"""
        with self._lock:
            if run_id in self._executions:
                raise ValueError(f"Execution {run_id} already exists")

            ctx = ExecutionContext(
                run_id=run_id,
                state=ExecutionState.PENDING,
                pipeline_id=pipeline_id,
                started_at=datetime.utcnow()
            )
            self._executions[run_id] = ctx

            # Queue execution command
            self._command_queue.put(('start', run_id))
            self._emit_event('execution_started', {'run_id': run_id})

            # Ensure executor thread is running
            self._ensure_executor_running()

            return ctx

    def pause_execution(self, run_id: str) -> bool:
        """Pause running execution"""
        with self._lock:
            ctx = self._executions.get(run_id)
            if not ctx or ctx.state != ExecutionState.RUNNING:
                return False

            ctx.pause_signal.set()
            ctx.state = ExecutionState.PAUSED
            self._emit_event('execution_paused', {'run_id': run_id})
            return True

    def resume_execution(self, run_id: str) -> bool:
        """Resume paused execution"""
        with self._lock:
            ctx = self._executions.get(run_id)
            if not ctx or ctx.state != ExecutionState.PAUSED:
                return False

            ctx.pause_signal.clear()
            ctx.resume_signal.set()
            ctx.state = ExecutionState.RUNNING
            self._emit_event('execution_resumed', {'run_id': run_id})
            return True

    def stop_execution(self, run_id: str, force: bool = False) -> bool:
        """Stop execution (graceful or forced)"""
        with self._lock:
            ctx = self._executions.get(run_id)
            if not ctx:
                return False

            if force:
                ctx.state = ExecutionState.STOPPED
                self._emit_event('execution_force_stopped', {'run_id': run_id})
            else:
                ctx.stop_signal.set()
                ctx.state = ExecutionState.STOPPING
                self._emit_event('execution_stopping', {'run_id': run_id})

            return True

    def get_execution_state(self, run_id: str) -> Optional[ExecutionContext]:
        """Get current execution state"""
        with self._lock:
            return self._executions.get(run_id)

    def list_active_executions(self) -> list:
        """List all active executions"""
        with self._lock:
            return [
                ctx for ctx in self._executions.values()
                if ctx.state in (ExecutionState.RUNNING, ExecutionState.PAUSED)
            ]

    def checkpoint(self, run_id: str, step_id: str, data: Dict[str, Any]):
        """Save checkpoint"""
        with self._lock:
            ctx = self._executions.get(run_id)
            if ctx:
                ctx.completed_steps.add(step_id)
                ctx.checkpoint_data[step_id] = data
                self._emit_event('checkpoint_saved', {
                    'run_id': run_id,
                    'step_id': step_id
                })

    def can_resume_from_checkpoint(self, run_id: str) -> bool:
        """Check if execution can resume from checkpoint"""
        with self._lock:
            ctx = self._executions.get(run_id)
            return ctx is not None and len(ctx.completed_steps) > 0

    def subscribe_events(self, callback: Callable[[str, dict], None]):
        """Subscribe to execution events"""
        self._event_callbacks.append(callback)

    def _emit_event(self, event_type: str, data: dict):
        """Emit event to all subscribers"""
        for callback in self._event_callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Event callback error: {e}")

    def _ensure_executor_running(self):
        """Ensure executor thread is running"""
        if not self._running:
            self._running = True
            self._executor_thread = threading.Thread(
                target=self._executor_loop,
                daemon=True,
                name="CoreExecutionEngine"
            )
            self._executor_thread.start()

    def _executor_loop(self):
        """Main execution loop"""
        logger.info("CoreExecutionEngine started")

        while self._running:
            try:
                # Process commands
                try:
                    command, run_id = self._command_queue.get(timeout=0.1)
                    self._process_command(command, run_id)
                except Empty:
                    pass

                # Check for pause/stop signals in active executions
                for ctx in self.list_active_executions():
                    if ctx.pause_signal.is_set():
                        logger.info(f"Execution {ctx.run_id} paused")
                    if ctx.stop_signal.is_set():
                        logger.info(f"Execution {ctx.run_id} stopping")
                        self._handle_stop(ctx.run_id)

            except Exception as e:
                logger.error(f"Executor loop error: {e}")

        logger.info("CoreExecutionEngine stopped")

    def _process_command(self, command: str, run_id: str):
        """Process execution command"""
        if command == 'start':
            # Delegate to actual runner
            self._emit_event('execution_command', {
                'command': 'start',
                'run_id': run_id
            })

    def _handle_stop(self, run_id: str):
        """Handle execution stop"""
        with self._lock:
            ctx = self._executions.get(run_id)
            if ctx:
                ctx.state = ExecutionState.STOPPED
                ctx.finished_at = datetime.utcnow()
                self._emit_event('execution_stopped', {'run_id': run_id})

    def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down CoreExecutionEngine")
        self._running = False

        # Stop all active executions
        for ctx in self.list_active_executions():
            self.stop_execution(ctx.run_id, force=True)

        if self._executor_thread:
            self._executor_thread.join(timeout=5)
```

**Integration:**
```python
# In src/ui/app.py
class ScraperPlatformApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)

        # Single execution engine for entire app
        self.execution_engine = CoreExecutionEngine()

        # Subscribe UI to execution events
        self.execution_engine.subscribe_events(self._on_execution_event)

    def _on_execution_event(self, event_type: str, data: dict):
        """Handle execution events"""
        # Update UI state via event bus
        if event_type == 'execution_started':
            self.event_bus.emit_job_state_changed(data['run_id'], 'running')
        elif event_type == 'execution_paused':
            self.event_bus.emit_job_state_changed(data['run_id'], 'paused')
```

**Benefits:**
✅ Single source of truth for ALL executions
✅ Proper signal propagation (pause/stop/resume)
✅ Checkpoint support built-in
✅ Thread-safe operations
✅ Event-driven UI updates

---

### 1.2 Desktop Scheduler (Airflow Replacement)

**Current Problem:**
- Airflow is overkill for desktop
- No persistent job queue
- Scheduling tied to external service

**Implementation:**

Create `src/scheduler/desktop_scheduler.py`:

```python
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
import threading
import time
import logging

logger = logging.getLogger(__name__)

@dataclass
class ScheduledJob:
    """Scheduled job definition"""
    job_id: str
    pipeline_id: str
    schedule_type: str  # 'once', 'interval', 'cron'
    schedule_config: Dict[str, Any]
    next_run: datetime
    enabled: bool = True
    last_run: Optional[datetime] = None
    run_count: int = 0

class DesktopScheduler:
    """
    Desktop-native scheduler (Airflow replacement).

    Features:
    - SQLite-backed persistent queue
    - Survives app restarts
    - Simple interval/cron scheduling
    - No external dependencies
    """

    def __init__(self, db_path: Path, execution_engine):
        self.db_path = db_path
        self.execution_engine = execution_engine
        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """Initialize scheduler database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_jobs (
                    job_id TEXT PRIMARY KEY,
                    pipeline_id TEXT NOT NULL,
                    schedule_type TEXT NOT NULL,
                    schedule_config TEXT NOT NULL,
                    next_run TEXT NOT NULL,
                    enabled INTEGER NOT NULL,
                    last_run TEXT,
                    run_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
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
                    FOREIGN KEY (job_id) REFERENCES scheduled_jobs(job_id)
                )
            """)

    def schedule_job(
        self,
        job_id: str,
        pipeline_id: str,
        schedule_type: str,
        schedule_config: Dict[str, Any]
    ) -> bool:
        """Add job to schedule"""
        next_run = self._calculate_next_run(schedule_type, schedule_config)

        job = ScheduledJob(
            job_id=job_id,
            pipeline_id=pipeline_id,
            schedule_type=schedule_type,
            schedule_config=schedule_config,
            next_run=next_run
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO scheduled_jobs
                (job_id, pipeline_id, schedule_type, schedule_config, next_run, enabled, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                job.job_id,
                job.pipeline_id,
                job.schedule_type,
                str(job.schedule_config),
                job.next_run.isoformat(),
                1,
                datetime.utcnow().isoformat()
            ))

        logger.info(f"Scheduled job: {job_id}, next run: {next_run}")
        return True

    def _calculate_next_run(self, schedule_type: str, config: Dict[str, Any]) -> datetime:
        """Calculate next run time"""
        if schedule_type == 'once':
            return config.get('run_at', datetime.utcnow())
        elif schedule_type == 'interval':
            minutes = config.get('interval_minutes', 60)
            return datetime.utcnow() + timedelta(minutes=minutes)
        elif schedule_type == 'cron':
            # Simple cron: run at specific hour/minute daily
            hour = config.get('hour', 0)
            minute = config.get('minute', 0)
            next_run = datetime.utcnow().replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= datetime.utcnow():
                next_run += timedelta(days=1)
            return next_run
        else:
            return datetime.utcnow()

    def get_due_jobs(self) -> List[ScheduledJob]:
        """Get jobs that are due to run"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT job_id, pipeline_id, schedule_type, schedule_config, next_run, last_run, run_count
                FROM scheduled_jobs
                WHERE enabled = 1 AND next_run <= ?
            """, (datetime.utcnow().isoformat(),))

            jobs = []
            for row in cursor:
                jobs.append(ScheduledJob(
                    job_id=row[0],
                    pipeline_id=row[1],
                    schedule_type=row[2],
                    schedule_config=eval(row[3]),  # Safe since we control the data
                    next_run=datetime.fromisoformat(row[4]),
                    last_run=datetime.fromisoformat(row[5]) if row[5] else None,
                    run_count=row[6]
                ))
            return jobs

    def start(self):
        """Start scheduler"""
        if self._running:
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
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        logger.info("DesktopScheduler stopped")

    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self._running:
            try:
                # Check for due jobs every 10 seconds
                due_jobs = self.get_due_jobs()

                for job in due_jobs:
                    self._execute_job(job)

                time.sleep(10)

            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(30)  # Back off on error

    def _execute_job(self, job: ScheduledJob):
        """Execute scheduled job"""
        run_id = f"{job.job_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        try:
            # Start execution via core engine
            self.execution_engine.start_execution(run_id, job.pipeline_id)

            # Update job record
            with sqlite3.connect(self.db_path) as conn:
                next_run = self._calculate_next_run(job.schedule_type, job.schedule_config)

                conn.execute("""
                    UPDATE scheduled_jobs
                    SET last_run = ?, run_count = run_count + 1, next_run = ?
                    WHERE job_id = ?
                """, (datetime.utcnow().isoformat(), next_run.isoformat(), job.job_id))

                # Record in history
                conn.execute("""
                    INSERT INTO job_history (job_id, run_id, started_at)
                    VALUES (?, ?, ?)
                """, (job.job_id, run_id, datetime.utcnow().isoformat()))

            logger.info(f"Executed scheduled job: {job.job_id} (run_id: {run_id})")

        except Exception as e:
            logger.error(f"Failed to execute job {job.job_id}: {e}")
```

**Usage:**
```python
# In src/ui/app.py
self.scheduler = DesktopScheduler(
    db_path=Path.home() / '.scraper-platform' / 'scheduler.db',
    execution_engine=self.execution_engine
)
self.scheduler.start()

# Schedule a job
self.scheduler.schedule_job(
    job_id='alfabeta-daily',
    pipeline_id='alfabeta',
    schedule_type='cron',
    schedule_config={'hour': 2, 'minute': 0}  # Run at 2 AM daily
)
```

---

## 🟡 PHASE 2: UI CONTROL PLANE (Weeks 5-8)

**Goal:** UI owns execution, not just displays it

### 2.1 UI-Commanded Execution

**Current Problem:**
- UI polls for state changes (2-second timer)
- `JobManager` runs jobs independently
- UI can't truly control execution

**Solution:**

Update `src/ui/main_window.py`:

```python
class MainWindow(QMainWindow):
    def __init__(self, user, rbac, execution_engine, scheduler):
        super().__init__()

        self.execution_engine = execution_engine
        self.scheduler = scheduler

        # Subscribe to execution events (pushed, not polled)
        self.execution_engine.subscribe_events(self._on_execution_event)

        # Remove polling timer
        # self.update_timer.start(2000)  # DELETE THIS

    def _start_job(self):
        """Start job via execution engine"""
        # UI commands the engine
        run_id = f"{source}-{timestamp}"
        ctx = self.execution_engine.start_execution(run_id, pipeline_id)

        # Update UI immediately (no polling)
        self.store.dispatch(Action(
            type=ActionType.JOB_STARTED,
            payload={'job_id': run_id, ...}
        ))

    def _pause_job(self, job_id: str):
        """Pause job via execution engine"""
        success = self.execution_engine.pause_execution(job_id)
        if success:
            # UI updated via event callback
            pass

    def _resume_job(self, job_id: str):
        """Resume job via execution engine"""
        success = self.execution_engine.resume_execution(job_id)

    def _stop_job(self, job_id: str):
        """Stop job via execution engine"""
        success = self.execution_engine.stop_execution(job_id)

    def _on_execution_event(self, event_type: str, data: dict):
        """React to execution events (event-driven, not polled)"""
        if event_type == 'execution_started':
            # Update UI in real-time
            self._update_job_display(data['run_id'], 'running')
        elif event_type == 'execution_paused':
            self._update_job_display(data['run_id'], 'paused')
        # etc.
```

---

## 🟢 PHASE 3: DEVELOPER EXPERIENCE (Weeks 9-12)

**Goal:** Debugging, observability, and maintainability

### 3.1 Session Replay (Production-Grade)

Create `src/replay/recorder.py`:

```python
class ProductionReplayRecorder:
    """Production-grade replay recording"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.sessions: Dict[str, ReplaySession] = {}

    def start_session(self, session_id: str):
        """Start recording session"""
        session = ReplaySession(
            session_id=session_id,
            start_time=datetime.utcnow(),
            events=[],
            network_log=[],
            screenshots=[]
        )
        self.sessions[session_id] = session

    def record_action(self, session_id: str, action_type: str, details: dict):
        """Record user/system action"""
        session = self.sessions.get(session_id)
        if session:
            session.events.append({
                'timestamp': (datetime.utcnow() - session.start_time).total_seconds(),
                'type': action_type,
                'details': details
            })

    def record_network(self, session_id: str, request: dict, response: dict):
        """Record network activity"""
        session = self.sessions.get(session_id)
        if session:
            session.network_log.append({
                'timestamp': (datetime.utcnow() - session.start_time).total_seconds(),
                'request': request,
                'response': response
            })

    def save_session(self, session_id: str):
        """Save session to disk"""
        session = self.sessions.get(session_id)
        if not session:
            return

        output_file = self.output_dir / f"{session_id}.replay.json"
        output_file.write_text(json.dumps({
            'metadata': {
                'session_id': session_id,
                'start_time': session.start_time.isoformat(),
                'duration': (datetime.utcnow() - session.start_time).total_seconds()
            },
            'events': session.events,
            'network_log': session.network_log,
            'screenshots': session.screenshots
        }, indent=2))
```

---

## 📊 Implementation Priority Matrix

| Feature | Impact | Effort | Priority | Weeks |
|---------|--------|--------|----------|-------|
| Core Execution Engine | 🔴 Critical | High | P0 | 1-2 |
| Desktop Scheduler | 🔴 Critical | Medium | P0 | 2-3 |
| UI Control Integration | 🔴 Critical | High | P0 | 3-4 |
| Checkpointing | 🟡 High | Medium | P1 | 5-6 |
| Resource Management | 🟡 High | Low | P1 | 6-7 |
| Session Replay | 🟡 High | High | P1 | 7-10 |
| Run Comparison UI | 🟢 Medium | Low | P2 | 11 |
| Plugin System | 🟢 Medium | High | P3 | 12+ |
| Agent Consolidation | 🟢 Low | High | P3 | 12+ |

---

## ✅ Definition of Done (Desktop Application)

### Must Have (Blocking Desktop 1.0)
- [ ] Single execution engine controls all jobs
- [ ] UI can start/pause/resume/stop jobs
- [ ] Desktop scheduler replaces Airflow
- [ ] Checkpoints survive crashes
- [ ] Graceful shutdown works
- [ ] Installer builds successfully
- [ ] Auto-update tested

### Should Have (Desktop 1.5)
- [ ] Session replay works end-to-end
- [ ] Resource limits enforced
- [ ] Run comparison UI
- [ ] Diagnostics export
- [ ] Authentication optional

### Nice to Have (Desktop 2.0)
- [ ] Plugin system
- [ ] Agent consolidation
- [ ] Advanced debugging tools

---

## 🚀 Quick Win: Replace Polling with Events

**Immediate impact (1 day):**

```python
# BEFORE (Polling - BAD)
self.update_timer = QTimer()
self.update_timer.timeout.connect(self._periodic_update)
self.update_timer.start(2000)  # Poll every 2 seconds

# AFTER (Event-driven - GOOD)
self.execution_engine.subscribe_events(self._on_execution_event)

def _on_execution_event(self, event_type, data):
    # Real-time updates, no polling!
    self._update_ui_immediately(event_type, data)
```

---

## 📝 Next Actions (This Week)

1. **Day 1-2:** Implement `CoreExecutionEngine`
2. **Day 3:** Wire to UI (remove polling timer)
3. **Day 4-5:** Test start/pause/resume/stop
4. **Weekend:** Implement `DesktopScheduler`
5. **Week 2:** Integration testing

---

**This roadmap transforms your platform from "backend with UI" to "true desktop application".**

The key is **Phase 1** - once you have a single execution engine and desktop scheduler, everything else becomes incremental improvements rather than architectural rewrites.
