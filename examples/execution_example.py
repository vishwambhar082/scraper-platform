"""
Example usage of CoreExecutionEngine and DesktopScheduler.
"""

import logging
import time
from pathlib import Path
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def example_basic_execution():
    """Example: Basic execution lifecycle"""
    from execution import CoreExecutionEngine

    print("\n=== Example: Basic Execution ===\n")

    # Create execution engine
    engine = CoreExecutionEngine()

    # Subscribe to events
    def on_event(event_type, data):
        print(f"Event: {event_type} - {data}")

    engine.subscribe_events(on_event)

    # Start execution
    ctx = engine.start_execution(
        run_id="example-001",
        pipeline_id="alfabeta",
        source="alfabeta",
        run_type="FULL_REFRESH",
        environment="dev"
    )

    print(f"Started execution: {ctx.run_id}")
    time.sleep(1)

    # Update progress
    engine.update_progress(
        run_id="example-001",
        progress=0.5,
        current_step="processing",
        completed_steps=1,
        total_steps=2
    )

    time.sleep(1)

    # Complete execution
    engine.complete_execution("example-001", success=True)

    print(f"Final state: {engine.get_execution_state('example-001').state}")

    # Cleanup
    engine.shutdown()


def example_pause_resume():
    """Example: Pause and resume execution"""
    from execution import CoreExecutionEngine

    print("\n=== Example: Pause and Resume ===\n")

    engine = CoreExecutionEngine()

    # Start execution
    ctx = engine.start_execution(
        run_id="example-002",
        pipeline_id="test",
        source="test"
    )

    time.sleep(0.5)

    # Pause
    print("Pausing execution...")
    engine.pause_execution("example-002")
    print(f"State: {engine.get_execution_state('example-002').state}")

    time.sleep(1)

    # Resume
    print("Resuming execution...")
    engine.resume_execution("example-002")
    print(f"State: {engine.get_execution_state('example-002').state}")

    time.sleep(1)

    # Complete
    engine.complete_execution("example-002", success=True)

    engine.shutdown()


def example_checkpointing():
    """Example: Checkpointing for crash recovery"""
    from execution import CoreExecutionEngine, CheckpointManager

    print("\n=== Example: Checkpointing ===\n")

    engine = CoreExecutionEngine()
    checkpoint_mgr = CheckpointManager(Path("checkpoints.db"))

    # Start execution
    ctx = engine.start_execution(
        run_id="example-003",
        pipeline_id="test",
        source="test"
    )

    # Save checkpoints as steps complete
    engine.checkpoint("example-003", "step-1", {"records": 100})
    print("Checkpoint 1 saved")

    engine.checkpoint("example-003", "step-2", {"records": 250})
    print("Checkpoint 2 saved")

    # Check if we can resume
    can_resume = engine.can_resume_from_checkpoint("example-003")
    print(f"Can resume from checkpoint: {can_resume}")

    # Get checkpoint data
    data = engine.get_checkpoint_data("example-003", "step-1")
    print(f"Step 1 checkpoint data: {data}")

    # Save execution state to database
    checkpoint_mgr.save_execution_state(
        run_id=ctx.run_id,
        pipeline_id=ctx.pipeline_id,
        source=ctx.source,
        run_type=ctx.run_type,
        environment=ctx.environment,
        state=ctx.state.value,
        started_at=ctx.started_at,
        progress=ctx.progress,
        current_step=ctx.current_step
    )

    print("Execution state saved to database")

    engine.shutdown()


def example_scheduling():
    """Example: Job scheduling"""
    from execution import CoreExecutionEngine
    from scheduler import DesktopScheduler, ScheduleConfig

    print("\n=== Example: Job Scheduling ===\n")

    engine = CoreExecutionEngine()
    scheduler = DesktopScheduler(Path("scheduler.db"), engine)

    # Schedule daily job
    config = ScheduleConfig.daily(hour=2, minute=0)
    scheduler.schedule_job(
        job_id="alfabeta-daily",
        pipeline_id="alfabeta",
        source="alfabeta",
        schedule_type=config['type'],
        schedule_config=config['config']
    )
    print("Scheduled daily job for 2:00 AM")

    # Schedule interval job
    config = ScheduleConfig.interval(hours=6)
    scheduler.schedule_job(
        job_id="quebec-6hourly",
        pipeline_id="quebec",
        source="quebec",
        schedule_type=config['type'],
        schedule_config=config['config']
    )
    print("Scheduled interval job for every 6 hours")

    # Schedule weekly job
    config = ScheduleConfig.weekly(day_of_week=0, hour=9, minute=0)  # Monday 9 AM
    scheduler.schedule_job(
        job_id="lafa-weekly",
        pipeline_id="lafa",
        source="lafa",
        schedule_type=config['type'],
        schedule_config=config['config']
    )
    print("Scheduled weekly job for Monday 9:00 AM")

    # List all scheduled jobs
    jobs = scheduler.get_scheduled_jobs()
    print(f"\nScheduled jobs ({len(jobs)}):")
    for job in jobs:
        print(f"  - {job.job_id}: next run at {job.next_run}")

    # Get scheduler stats
    stats = scheduler.get_stats()
    print(f"\nScheduler stats: {stats}")

    # Start scheduler (this would run in background)
    # scheduler.start()

    # Cleanup
    scheduler.stop()
    engine.shutdown()


def example_resource_monitoring():
    """Example: Resource monitoring"""
    from execution import ResourceMonitor

    print("\n=== Example: Resource Monitoring ===\n")

    # Create monitor with limits
    monitor = ResourceMonitor(
        sample_interval=1.0,
        cpu_limit_percent=80.0,
        memory_limit_mb=2048
    )

    # Subscribe to limit exceeded events
    def on_limit_exceeded(resource_type, value):
        print(f"ALERT: {resource_type} limit exceeded: {value}")

    monitor.subscribe_limit_exceeded(on_limit_exceeded)

    # Start monitoring
    monitor.start()

    # Let it run for a few seconds
    for i in range(5):
        time.sleep(1)
        snapshot = monitor.get_current_snapshot()
        if snapshot:
            print(f"CPU: {snapshot.cpu_percent:.1f}%, "
                  f"Memory: {snapshot.memory_percent:.1f}%, "
                  f"Disk: {snapshot.disk_percent:.1f}%")

    # Get stats
    stats = monitor.get_stats()
    print(f"\nMonitor stats: {stats}")

    # Stop monitoring
    monitor.stop()


def example_integration():
    """Example: Full integration with UI"""
    from execution import CoreExecutionEngine
    from scheduler import DesktopScheduler
    from ui.state import AppStore, EventBus
    from ui.app_integration import ExecutionIntegration

    print("\n=== Example: Full Integration ===\n")

    # Create UI components
    store = AppStore()
    event_bus = EventBus()

    # Create integration
    integration = ExecutionIntegration(store, event_bus)

    # Start all components
    integration.start()

    # Start a job
    run_id = integration.start_job(
        source="alfabeta",
        run_type="FULL_REFRESH",
        environment="dev"
    )
    print(f"Started job: {run_id}")

    time.sleep(1)

    # Get job status
    status = integration.get_job_status(run_id)
    print(f"Job status: {status.state if status else 'not found'}")

    # Schedule a job
    from scheduler import ScheduleConfig
    config = ScheduleConfig.daily(hour=3, minute=0)

    integration.schedule_job(
        job_id="alfabeta-scheduled",
        source="alfabeta",
        schedule_type=config['type'],
        schedule_config=config['config']
    )
    print("Scheduled daily job")

    # Get comprehensive stats
    stats = integration.get_stats()
    print(f"\nIntegration stats:")
    print(f"  Execution engine: {stats['execution_engine']}")
    print(f"  Scheduler: {stats['scheduler']}")
    print(f"  Resources: {stats['resources']}")

    # Shutdown
    integration.shutdown()


if __name__ == "__main__":
    print("CoreExecutionEngine and DesktopScheduler Examples")
    print("=" * 60)

    # Run examples
    example_basic_execution()
    example_pause_resume()
    example_checkpointing()
    example_scheduling()
    example_resource_monitoring()
    example_integration()

    print("\n" + "=" * 60)
    print("All examples completed!")
