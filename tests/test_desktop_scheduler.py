"""
Tests for DesktopScheduler.
"""

import pytest
import time
from pathlib import Path
from datetime import datetime, timedelta
from tempfile import TemporaryDirectory

from execution import CoreExecutionEngine
from scheduler import DesktopScheduler, ScheduleConfig


class TestDesktopScheduler:
    """Test suite for DesktopScheduler"""

    @pytest.fixture
    def engine(self):
        """Create execution engine"""
        engine = CoreExecutionEngine()
        yield engine
        engine.shutdown()

    @pytest.fixture
    def scheduler(self, engine):
        """Create scheduler"""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "scheduler.db"
            sched = DesktopScheduler(db_path, engine)
            yield sched
            sched.stop()

    def test_schedule_job(self, scheduler):
        """Test scheduling a job"""
        config = ScheduleConfig.daily(hour=2, minute=0)

        success = scheduler.schedule_job(
            job_id="test-job-1",
            pipeline_id="test-pipeline",
            source="test-source",
            schedule_type=config['type'],
            schedule_config=config['config']
        )

        assert success is True

        # Verify job was saved
        jobs = scheduler.get_scheduled_jobs()
        assert len(jobs) == 1
        assert jobs[0].job_id == "test-job-1"

    def test_unschedule_job(self, scheduler):
        """Test unscheduling a job"""
        config = ScheduleConfig.daily(hour=2, minute=0)

        scheduler.schedule_job(
            job_id="test-job-2",
            pipeline_id="test-pipeline",
            source="test-source",
            schedule_type=config['type'],
            schedule_config=config['config']
        )

        # Unschedule
        success = scheduler.unschedule_job("test-job-2")
        assert success is True

        # Verify job was removed
        jobs = scheduler.get_scheduled_jobs()
        assert len(jobs) == 0

    def test_enable_disable_job(self, scheduler):
        """Test enabling and disabling jobs"""
        config = ScheduleConfig.daily(hour=2, minute=0)

        scheduler.schedule_job(
            job_id="test-job-3",
            pipeline_id="test-pipeline",
            source="test-source",
            schedule_type=config['type'],
            schedule_config=config['config']
        )

        # Disable job
        scheduler.disable_job("test-job-3")

        jobs = scheduler.get_scheduled_jobs()
        assert jobs[0].enabled is False

        # Enable job
        scheduler.enable_job("test-job-3")

        jobs = scheduler.get_scheduled_jobs()
        assert jobs[0].enabled is True

    def test_interval_scheduling(self, scheduler):
        """Test interval-based scheduling"""
        config = ScheduleConfig.interval(minutes=30)

        scheduler.schedule_job(
            job_id="test-interval",
            pipeline_id="test-pipeline",
            source="test-source",
            schedule_type=config['type'],
            schedule_config=config['config']
        )

        jobs = scheduler.get_scheduled_jobs()
        job = jobs[0]

        # Next run should be ~30 minutes from now
        expected_next = datetime.utcnow() + timedelta(minutes=30)
        time_diff = abs((job.next_run - expected_next).total_seconds())
        assert time_diff < 60  # Within 1 minute

    def test_cron_scheduling(self, scheduler):
        """Test cron-based scheduling"""
        config = ScheduleConfig.daily(hour=2, minute=30)

        scheduler.schedule_job(
            job_id="test-cron",
            pipeline_id="test-pipeline",
            source="test-source",
            schedule_type=config['type'],
            schedule_config=config['config']
        )

        jobs = scheduler.get_scheduled_jobs()
        job = jobs[0]

        # Next run should be at 2:30 AM
        assert job.next_run.hour == 2
        assert job.next_run.minute == 30

    def test_weekly_scheduling(self, scheduler):
        """Test weekly scheduling"""
        config = ScheduleConfig.weekly(day_of_week=0, hour=9, minute=0)  # Monday 9 AM

        scheduler.schedule_job(
            job_id="test-weekly",
            pipeline_id="test-pipeline",
            source="test-source",
            schedule_type=config['type'],
            schedule_config=config['config']
        )

        jobs = scheduler.get_scheduled_jobs()
        job = jobs[0]

        # Next run should be on Monday
        assert job.next_run.weekday() == 0
        assert job.next_run.hour == 9
        assert job.next_run.minute == 0

    def test_manual_scheduling(self, scheduler):
        """Test manual-only scheduling"""
        config = ScheduleConfig.manual()

        scheduler.schedule_job(
            job_id="test-manual",
            pipeline_id="test-pipeline",
            source="test-source",
            schedule_type=config['type'],
            schedule_config=config['config']
        )

        jobs = scheduler.get_scheduled_jobs()
        job = jobs[0]

        # Next run should be far future (datetime.max)
        assert job.next_run.year == datetime.max.year

    def test_get_due_jobs(self, scheduler):
        """Test getting due jobs"""
        # Schedule job for 1 minute ago (should be due)
        past_time = datetime.utcnow() - timedelta(minutes=1)
        config = ScheduleConfig.once(past_time)

        scheduler.schedule_job(
            job_id="test-due",
            pipeline_id="test-pipeline",
            source="test-source",
            schedule_type=config['type'],
            schedule_config=config['config']
        )

        # Schedule job for future (not due)
        future_time = datetime.utcnow() + timedelta(hours=1)
        config2 = ScheduleConfig.once(future_time)

        scheduler.schedule_job(
            job_id="test-future",
            pipeline_id="test-pipeline",
            source="test-source",
            schedule_type=config2['type'],
            schedule_config=config2['config']
        )

        # Get due jobs
        due = scheduler.get_due_jobs()

        # Only past job should be due
        assert len(due) == 1
        assert due[0].job_id == "test-due"

    def test_scheduler_execution(self, scheduler, engine):
        """Test that scheduler executes due jobs"""
        # Schedule job for immediate execution
        past_time = datetime.utcnow() - timedelta(seconds=1)
        config = ScheduleConfig.once(past_time)

        scheduler.schedule_job(
            job_id="test-exec",
            pipeline_id="test-pipeline",
            source="test-source",
            schedule_type=config['type'],
            schedule_config=config['config']
        )

        # Start scheduler
        scheduler.start()
        time.sleep(15)  # Wait for scheduler loop to execute

        # Check that execution was started
        jobs = scheduler.get_scheduled_jobs()
        job = jobs[0]

        assert job.run_count >= 1
        assert job.last_run is not None

    def test_job_history(self, scheduler):
        """Test job history tracking"""
        # Schedule and manually execute
        config = ScheduleConfig.manual()

        scheduler.schedule_job(
            job_id="test-history",
            pipeline_id="test-pipeline",
            source="test-source",
            schedule_type=config['type'],
            schedule_config=config['config']
        )

        # Get history (should be empty)
        history = scheduler.get_job_history("test-history")
        assert len(history) == 0

    def test_scheduler_stats(self, scheduler):
        """Test scheduler statistics"""
        # Schedule some jobs
        config = ScheduleConfig.daily(hour=2, minute=0)

        scheduler.schedule_job(
            job_id="stats-job-1",
            pipeline_id="test-pipeline",
            source="test-source",
            schedule_type=config['type'],
            schedule_config=config['config']
        )

        scheduler.schedule_job(
            job_id="stats-job-2",
            pipeline_id="test-pipeline",
            source="test-source",
            schedule_type=config['type'],
            schedule_config=config['config'],
            enabled=False
        )

        stats = scheduler.get_stats()

        assert stats['total_jobs'] == 2
        assert stats['enabled_jobs'] == 1
        assert 'total_runs' in stats

    def test_scheduler_start_stop(self, scheduler):
        """Test scheduler start and stop"""
        # Start scheduler
        scheduler.start()
        assert scheduler._running is True

        # Stop scheduler
        scheduler.stop()
        assert scheduler._running is False

    def test_persistence(self, engine):
        """Test that scheduled jobs persist across restarts"""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "scheduler.db"

            # Create scheduler and schedule job
            scheduler1 = DesktopScheduler(db_path, engine)
            config = ScheduleConfig.daily(hour=3, minute=0)

            scheduler1.schedule_job(
                job_id="persist-job",
                pipeline_id="test-pipeline",
                source="test-source",
                schedule_type=config['type'],
                schedule_config=config['config']
            )

            # Create new scheduler instance (simulating restart)
            scheduler2 = DesktopScheduler(db_path, engine)

            # Job should still be there
            jobs = scheduler2.get_scheduled_jobs()
            assert len(jobs) == 1
            assert jobs[0].job_id == "persist-job"

            scheduler1.stop()
            scheduler2.stop()
