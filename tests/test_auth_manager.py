"""
Tests for authentication manager and security UI.
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from ui.security import AuthManager, IdleMonitor
from datetime import datetime, timedelta


class TestAuthManager:
    """Test authentication manager."""

    @pytest.fixture
    def auth_manager(self):
        """Create auth manager."""
        with TemporaryDirectory() as tmpdir:
            yield AuthManager(Path(tmpdir))

    def test_init(self, auth_manager):
        """Test initialization."""
        assert not auth_manager.has_pin()
        assert not auth_manager.is_auto_lock_enabled()

    def test_set_pin(self, auth_manager):
        """Test setting PIN."""
        auth_manager.set_pin("1234")
        assert auth_manager.has_pin()

    def test_verify_pin(self, auth_manager):
        """Test PIN verification."""
        auth_manager.set_pin("1234")

        # Correct PIN
        assert auth_manager.verify_pin("1234") is True

        # Incorrect PIN
        assert auth_manager.verify_pin("5678") is False

    def test_no_pin_configured(self, auth_manager):
        """Test verification with no PIN."""
        # Should pass if no PIN configured
        assert auth_manager.verify_pin("anything") is True

    def test_auto_lock_config(self, auth_manager):
        """Test auto-lock configuration."""
        auth_manager.set_auto_lock(True, 30)

        assert auth_manager.is_auto_lock_enabled() is True
        assert auth_manager.get_auto_lock_minutes() == 30

        # Disable
        auth_manager.set_auto_lock(False)
        assert auth_manager.is_auto_lock_enabled() is False

    def test_require_pin_on_start(self, auth_manager):
        """Test PIN on start configuration."""
        auth_manager.set_require_pin_on_start(True)
        assert auth_manager.is_pin_required_on_start() is True

        auth_manager.set_require_pin_on_start(False)
        assert auth_manager.is_pin_required_on_start() is False

    def test_security_audit_log(self, auth_manager):
        """Test security event logging."""
        auth_manager.log_security_event('test_event', {'key': 'value'})

        events = auth_manager.get_audit_events()
        assert len(events) == 1
        assert events[0]['event_type'] == 'test_event'
        assert events[0]['data']['key'] == 'value'

    def test_audit_events_limit(self, auth_manager):
        """Test audit events limit."""
        # Log many events
        for i in range(150):
            auth_manager.log_security_event(f'event_{i}', {})

        # Get limited events
        events = auth_manager.get_audit_events(limit=50)
        assert len(events) == 50

    def test_persistence(self):
        """Test configuration persistence."""
        with TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            # Create and configure
            auth1 = AuthManager(config_dir)
            auth1.set_pin("1234")
            auth1.set_auto_lock(True, 20)

            # Create new instance (simulating restart)
            auth2 = AuthManager(config_dir)

            # Verify persisted
            assert auth2.has_pin()
            assert auth2.verify_pin("1234")
            assert auth2.is_auto_lock_enabled()
            assert auth2.get_auto_lock_minutes() == 20


class TestIdleMonitor:
    """Test idle monitor."""

    def test_init(self):
        """Test initialization."""
        monitor = IdleMonitor(timeout_minutes=15)
        assert not monitor.is_idle()

    def test_reset(self):
        """Test activity reset."""
        monitor = IdleMonitor(timeout_minutes=1)

        # Wait a bit
        import time
        time.sleep(0.1)

        # Reset
        monitor.reset()

        # Should not be idle
        assert not monitor.is_idle()

    def test_idle_detection(self):
        """Test idle detection."""
        monitor = IdleMonitor(timeout_minutes=1)

        # Manually set last activity to past
        monitor.last_activity = datetime.utcnow() - timedelta(minutes=2)

        # Should be idle
        assert monitor.is_idle()

    def test_idle_minutes(self):
        """Test getting idle minutes."""
        monitor = IdleMonitor(timeout_minutes=15)

        # Manually set last activity
        monitor.last_activity = datetime.utcnow() - timedelta(minutes=5)

        idle_minutes = monitor.get_idle_minutes()
        assert idle_minutes >= 4.9  # Account for timing
        assert idle_minutes <= 5.1
