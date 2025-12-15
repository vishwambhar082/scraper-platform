"""
Access lock screen for desktop security.
"""

import hashlib
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QCheckBox
)
from PySide6.QtCore import Qt, Signal

logger = logging.getLogger(__name__)


class LockScreen(QDialog):
    """
    PIN/Password lock screen for desktop application.

    Features:
    - PIN or password authentication
    - Configurable lock timeout
    - Failed attempt tracking
    - Auto-lock on idle
    """

    authenticated = Signal()
    lock_requested = Signal()

    def __init__(self, auth_manager, parent=None):
        super().__init__(parent)
        self.auth_manager = auth_manager
        self.attempt_count = 0
        self.max_attempts = 5

        self._init_ui()
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setModal(True)

    def _init_ui(self):
        """Initialize UI components."""
        self.setWindowTitle("Locked")
        self.setFixedSize(400, 300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Logo/Icon
        logo_label = QLabel("🔒")
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet("font-size: 48px;")
        layout.addWidget(logo_label)

        # Title
        title_label = QLabel("Application Locked")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title_label)

        # Message
        self.message_label = QLabel("Enter PIN or password to unlock")
        self.message_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.message_label)

        # PIN/Password input
        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setPlaceholderText("Enter PIN or password")
        self.pin_input.returnPressed.connect(self._on_unlock_clicked)
        layout.addWidget(self.pin_input)

        # Show password checkbox
        self.show_password_check = QCheckBox("Show password")
        self.show_password_check.toggled.connect(self._on_show_password_toggled)
        layout.addWidget(self.show_password_check)

        # Unlock button
        self.unlock_btn = QPushButton("Unlock")
        self.unlock_btn.clicked.connect(self._on_unlock_clicked)
        self.unlock_btn.setDefault(True)
        layout.addWidget(self.unlock_btn)

        # Attempts remaining
        self.attempts_label = QLabel("")
        self.attempts_label.setAlignment(Qt.AlignCenter)
        self.attempts_label.setStyleSheet("color: red;")
        layout.addWidget(self.attempts_label)

        layout.addStretch()

    def _on_show_password_toggled(self, checked: bool):
        """Handle show password toggle."""
        self.pin_input.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)

    def _on_unlock_clicked(self):
        """Handle unlock button click."""
        pin = self.pin_input.text()

        if not pin:
            self.message_label.setText("Please enter PIN or password")
            return

        # Verify PIN
        if self.auth_manager.verify_pin(pin):
            logger.info("Authentication successful")
            self.attempt_count = 0
            self.authenticated.emit()
            self.accept()
        else:
            self.attempt_count += 1
            remaining = self.max_attempts - self.attempt_count

            logger.warning(f"Authentication failed. Attempts remaining: {remaining}")

            if remaining > 0:
                self.message_label.setText("Incorrect PIN or password")
                self.attempts_label.setText(f"{remaining} attempts remaining")
                self.pin_input.clear()
                self.pin_input.setFocus()
            else:
                # Max attempts reached
                self.message_label.setText("Max attempts reached. Application will close.")
                self.unlock_btn.setEnabled(False)
                self.pin_input.setEnabled(False)

                # Log security event
                self.auth_manager.log_security_event(
                    'max_attempts_reached',
                    {'attempts': self.max_attempts}
                )

                # Close after delay
                from PySide6.QtCore import QTimer
                QTimer.singleShot(3000, self.reject)

    def showEvent(self, event):
        """Handle show event."""
        super().showEvent(event)
        self.pin_input.clear()
        self.pin_input.setFocus()
        self.attempt_count = 0
        self.attempts_label.clear()
        self.message_label.setText("Enter PIN or password to unlock")


class SetupPinDialog(QDialog):
    """Dialog for setting up PIN/password."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pin_value: Optional[str] = None

        self._init_ui()

    def _init_ui(self):
        """Initialize UI."""
        self.setWindowTitle("Setup Security PIN")
        self.setFixedSize(400, 250)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        # Title
        title_label = QLabel("Setup Security PIN")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # Description
        desc_label = QLabel(
            "Set a PIN (4-8 digits) or password to protect your application.\n"
            "You will need this to unlock the application when locked."
        )
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # PIN input
        layout.addWidget(QLabel("Enter PIN/Password:"))
        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setPlaceholderText("Minimum 4 characters")
        layout.addWidget(self.pin_input)

        # Confirm input
        layout.addWidget(QLabel("Confirm PIN/Password:"))
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setPlaceholderText("Re-enter to confirm")
        layout.addWidget(self.confirm_input)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._on_save_clicked)
        save_btn.setDefault(True)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _on_save_clicked(self):
        """Handle save button click."""
        pin = self.pin_input.text()
        confirm = self.confirm_input.text()

        # Validation
        if not pin:
            QMessageBox.warning(self, "Error", "PIN cannot be empty")
            return

        if len(pin) < 4:
            QMessageBox.warning(self, "Error", "PIN must be at least 4 characters")
            return

        if pin != confirm:
            QMessageBox.warning(self, "Error", "PINs do not match")
            return

        self.pin_value = pin
        self.accept()

    def get_pin(self) -> Optional[str]:
        """Get entered PIN."""
        return self.pin_value


class AuthManager:
    """
    Authentication manager for desktop security.

    Features:
    - PIN/password storage (hashed)
    - Auto-lock configuration
    - Security audit log
    """

    def __init__(self, config_dir: Path):
        """
        Initialize auth manager.

        Args:
            config_dir: Configuration directory
        """
        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.auth_file = config_dir / "auth.json"
        self.audit_file = config_dir / "security_audit.log"

        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Load authentication configuration."""
        if self.auth_file.exists():
            try:
                return json.loads(self.auth_file.read_text())
            except Exception as e:
                logger.error(f"Failed to load auth config: {e}")
                return self._default_config()
        return self._default_config()

    def _default_config(self) -> dict:
        """Get default configuration."""
        return {
            'pin_hash': None,
            'auto_lock_enabled': False,
            'auto_lock_minutes': 15,
            'require_pin_on_start': False
        }

    def _save_config(self):
        """Save authentication configuration."""
        try:
            self.auth_file.write_text(json.dumps(self.config, indent=2))
        except Exception as e:
            logger.error(f"Failed to save auth config: {e}")

    def has_pin(self) -> bool:
        """Check if PIN is configured."""
        return self.config.get('pin_hash') is not None

    def set_pin(self, pin: str):
        """
        Set new PIN.

        Args:
            pin: Plain text PIN
        """
        pin_hash = self._hash_pin(pin)
        self.config['pin_hash'] = pin_hash
        self._save_config()

        self.log_security_event('pin_set', {})
        logger.info("PIN configured")

    def verify_pin(self, pin: str) -> bool:
        """
        Verify PIN.

        Args:
            pin: Plain text PIN to verify

        Returns:
            True if PIN matches, False otherwise
        """
        if not self.has_pin():
            return True  # No PIN configured

        pin_hash = self._hash_pin(pin)
        match = pin_hash == self.config.get('pin_hash')

        self.log_security_event(
            'pin_verification',
            {'success': match}
        )

        return match

    def _hash_pin(self, pin: str) -> str:
        """
        Hash PIN using SHA256.

        Args:
            pin: Plain text PIN

        Returns:
            Hashed PIN
        """
        return hashlib.sha256(pin.encode()).hexdigest()

    def set_auto_lock(self, enabled: bool, minutes: int = 15):
        """
        Configure auto-lock.

        Args:
            enabled: Enable auto-lock
            minutes: Minutes of inactivity before lock
        """
        self.config['auto_lock_enabled'] = enabled
        self.config['auto_lock_minutes'] = minutes
        self._save_config()

        self.log_security_event('auto_lock_configured', {
            'enabled': enabled,
            'minutes': minutes
        })

    def is_auto_lock_enabled(self) -> bool:
        """Check if auto-lock is enabled."""
        return self.config.get('auto_lock_enabled', False)

    def get_auto_lock_minutes(self) -> int:
        """Get auto-lock timeout in minutes."""
        return self.config.get('auto_lock_minutes', 15)

    def set_require_pin_on_start(self, require: bool):
        """
        Set whether PIN is required on application start.

        Args:
            require: Require PIN on start
        """
        self.config['require_pin_on_start'] = require
        self._save_config()

    def is_pin_required_on_start(self) -> bool:
        """Check if PIN is required on start."""
        return self.config.get('require_pin_on_start', False)

    def log_security_event(self, event_type: str, data: dict):
        """
        Log security event to audit log.

        Args:
            event_type: Type of event
            data: Event data
        """
        try:
            event = {
                'timestamp': datetime.utcnow().isoformat(),
                'event_type': event_type,
                'data': data
            }

            with open(self.audit_file, 'a') as f:
                f.write(json.dumps(event) + '\n')

        except Exception as e:
            logger.error(f"Failed to log security event: {e}")

    def get_audit_events(self, limit: int = 100) -> list:
        """
        Get recent security audit events.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of audit events
        """
        if not self.audit_file.exists():
            return []

        try:
            lines = self.audit_file.read_text().splitlines()
            recent_lines = lines[-limit:] if len(lines) > limit else lines

            events = []
            for line in recent_lines:
                try:
                    events.append(json.loads(line))
                except Exception:
                    pass

            return list(reversed(events))

        except Exception as e:
            logger.error(f"Failed to read audit log: {e}")
            return []


class IdleMonitor:
    """
    Monitor user activity for auto-lock.
    """

    def __init__(self, timeout_minutes: int = 15):
        """
        Initialize idle monitor.

        Args:
            timeout_minutes: Minutes before considering idle
        """
        self.timeout_minutes = timeout_minutes
        self.last_activity = datetime.utcnow()

    def reset(self):
        """Reset activity timer."""
        self.last_activity = datetime.utcnow()

    def is_idle(self) -> bool:
        """
        Check if user is idle.

        Returns:
            True if idle timeout reached
        """
        elapsed = datetime.utcnow() - self.last_activity
        return elapsed > timedelta(minutes=self.timeout_minutes)

    def get_idle_minutes(self) -> float:
        """
        Get minutes since last activity.

        Returns:
            Minutes idle
        """
        elapsed = datetime.utcnow() - self.last_activity
        return elapsed.total_seconds() / 60
