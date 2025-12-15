"""
Security audit log viewer.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QPushButton,
    QLineEdit, QComboBox, QHeaderView, QTextEdit,
    QDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal

logger = logging.getLogger(__name__)


class AuditViewer(QWidget):
    """
    Security audit log viewer.

    Shows:
    - Authentication attempts
    - Configuration changes
    - Security events
    - System access logs
    """

    def __init__(self, audit_file: Path, parent=None):
        super().__init__(parent)
        self.audit_file = audit_file
        self.events: List[Dict[str, Any]] = []

        self._init_ui()
        self.load_events()

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h2>Security Audit Log</h2>"))
        header_layout.addStretch()

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_events)
        header_layout.addWidget(refresh_btn)

        # Export button
        export_btn = QPushButton("Export Log")
        export_btn.clicked.connect(self._on_export_clicked)
        header_layout.addWidget(export_btn)

        # Clear button
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self._on_clear_clicked)
        header_layout.addWidget(clear_btn)

        layout.addLayout(header_layout)

        # Filters
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Event Type:"))
        self.event_type_filter = QComboBox()
        self.event_type_filter.addItem("All")
        self.event_type_filter.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.event_type_filter)

        filter_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search events...")
        self.search_input.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.search_input)

        filter_layout.addStretch()

        self.event_count_label = QLabel("0 events")
        filter_layout.addWidget(self.event_count_label)

        layout.addLayout(filter_layout)

        # Events table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Timestamp", "Event Type", "Status", "Details"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)

        layout.addWidget(self.table)

    def load_events(self):
        """Load events from audit log."""
        if not self.audit_file.exists():
            self.events = []
            self._populate_table([])
            return

        try:
            lines = self.audit_file.read_text().splitlines()
            self.events = []

            for line in lines:
                try:
                    event = json.loads(line)
                    self.events.append(event)
                except Exception as e:
                    logger.error(f"Failed to parse audit line: {e}")

            # Reverse to show most recent first
            self.events.reverse()

            # Update event type filter
            event_types = set(e.get('event_type', '') for e in self.events)
            current = self.event_type_filter.currentText()
            self.event_type_filter.clear()
            self.event_type_filter.addItem("All")
            self.event_type_filter.addItems(sorted(event_types))
            if current != "All" and current in event_types:
                self.event_type_filter.setCurrentText(current)

            self._apply_filters()

        except Exception as e:
            logger.error(f"Failed to load audit log: {e}")
            self.events = []
            self._populate_table([])

    def _apply_filters(self):
        """Apply current filters to table."""
        event_type_filter = self.event_type_filter.currentText()
        search_text = self.search_input.text().lower()

        filtered = []
        for event in self.events:
            # Event type filter
            if event_type_filter != "All" and event.get('event_type') != event_type_filter:
                continue

            # Search filter
            if search_text:
                event_str = json.dumps(event).lower()
                if search_text not in event_str:
                    continue

            filtered.append(event)

        self._populate_table(filtered)
        self.event_count_label.setText(f"{len(filtered)} events")

    def _populate_table(self, events: List[Dict[str, Any]]):
        """Populate table with events."""
        self.table.setRowCount(len(events))

        for row, event in enumerate(events):
            # Timestamp
            timestamp = event.get('timestamp', '')
            try:
                dt = datetime.fromisoformat(timestamp)
                timestamp_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                timestamp_str = timestamp

            self.table.setItem(row, 0, QTableWidgetItem(timestamp_str))

            # Event type
            event_type = event.get('event_type', '')
            self.table.setItem(row, 1, QTableWidgetItem(event_type))

            # Status (from data if available)
            data = event.get('data', {})
            status = "Success" if data.get('success', True) else "Failed"
            status_item = QTableWidgetItem(status)

            if status == "Failed":
                status_item.setBackground(Qt.red)
            else:
                status_item.setBackground(Qt.green)

            self.table.setItem(row, 2, status_item)

            # Details (summary of data)
            details = self._format_details(data)
            self.table.setItem(row, 3, QTableWidgetItem(details))

    def _format_details(self, data: Dict[str, Any]) -> str:
        """Format event data for display."""
        if not data:
            return ""

        # Format key information
        parts = []
        for key, value in data.items():
            if key == 'success':
                continue  # Already shown in status
            parts.append(f"{key}: {value}")

        return ", ".join(parts)[:100]

    def _on_row_double_clicked(self, row: int, col: int):
        """Handle row double-click to show details."""
        if row >= len(self.events):
            return

        event = self.events[row]
        dialog = EventDetailsDialog(event, self)
        dialog.exec()

    def _on_export_clicked(self):
        """Export audit log to file."""
        from PySide6.QtWidgets import QFileDialog

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Audit Log",
            f"audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json)"
        )

        if filename:
            try:
                with open(filename, 'w') as f:
                    json.dump(self.events, f, indent=2)

                QMessageBox.information(
                    self,
                    "Success",
                    f"Audit log exported to:\n{filename}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to export log:\n{str(e)}"
                )

    def _on_clear_clicked(self):
        """Clear audit log after confirmation."""
        reply = QMessageBox.question(
            self,
            "Clear Audit Log",
            "Are you sure you want to clear the entire audit log?\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                if self.audit_file.exists():
                    self.audit_file.unlink()

                self.events = []
                self._populate_table([])
                self.event_count_label.setText("0 events")

                QMessageBox.information(
                    self,
                    "Success",
                    "Audit log cleared"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to clear log:\n{str(e)}"
                )


class EventDetailsDialog(QDialog):
    """Dialog showing full event details."""

    def __init__(self, event: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.event = event

        self._init_ui()

    def _init_ui(self):
        """Initialize UI."""
        self.setWindowTitle("Event Details")
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout(self)

        # Header
        timestamp = self.event.get('timestamp', '')
        event_type = self.event.get('event_type', '')

        header_label = QLabel(f"<h3>{event_type}</h3>")
        layout.addWidget(header_label)

        timestamp_label = QLabel(f"<b>Timestamp:</b> {timestamp}")
        layout.addWidget(timestamp_label)

        # Event details
        details_label = QLabel("<b>Event Data:</b>")
        layout.addWidget(details_label)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setFontFamily("Courier")
        self.details_text.setPlainText(
            json.dumps(self.event, indent=2)
        )
        layout.addWidget(self.details_text)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class SecuritySettings(QWidget):
    """
    Security settings widget.

    Allows configuring:
    - PIN/password
    - Auto-lock
    - Audit log retention
    """

    settings_changed = Signal()

    def __init__(self, auth_manager, parent=None):
        super().__init__(parent)
        self.auth_manager = auth_manager

        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)

        # Header
        layout.addWidget(QLabel("<h2>Security Settings</h2>"))

        # PIN section
        pin_layout = QHBoxLayout()
        pin_layout.addWidget(QLabel("PIN/Password Protection:"))

        self.pin_status_label = QLabel()
        pin_layout.addWidget(self.pin_status_label)

        self.set_pin_btn = QPushButton("Set PIN")
        self.set_pin_btn.clicked.connect(self._on_set_pin_clicked)
        pin_layout.addWidget(self.set_pin_btn)

        self.remove_pin_btn = QPushButton("Remove PIN")
        self.remove_pin_btn.clicked.connect(self._on_remove_pin_clicked)
        pin_layout.addWidget(self.remove_pin_btn)

        pin_layout.addStretch()
        layout.addLayout(pin_layout)

        # Require PIN on start
        from PySide6.QtWidgets import QCheckBox

        self.require_pin_check = QCheckBox("Require PIN on application start")
        self.require_pin_check.toggled.connect(self._on_settings_changed)
        layout.addWidget(self.require_pin_check)

        # Auto-lock section
        autolock_layout = QHBoxLayout()
        autolock_layout.addWidget(QLabel("Auto-lock after idle:"))

        from PySide6.QtWidgets import QSpinBox

        self.autolock_spin = QSpinBox()
        self.autolock_spin.setMinimum(1)
        self.autolock_spin.setMaximum(120)
        self.autolock_spin.setSuffix(" minutes")
        self.autolock_spin.valueChanged.connect(self._on_settings_changed)
        autolock_layout.addWidget(self.autolock_spin)

        from PySide6.QtWidgets import QCheckBox

        self.autolock_enabled = QCheckBox("Enable")
        self.autolock_enabled.toggled.connect(self._on_settings_changed)
        autolock_layout.addWidget(self.autolock_enabled)

        autolock_layout.addStretch()
        layout.addLayout(autolock_layout)

        # Save button
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self._on_save_clicked)
        layout.addWidget(save_btn)

        layout.addStretch()

    def _load_settings(self):
        """Load current settings."""
        # PIN status
        if self.auth_manager.has_pin():
            self.pin_status_label.setText("✓ PIN configured")
            self.pin_status_label.setStyleSheet("color: green;")
            self.remove_pin_btn.setEnabled(True)
        else:
            self.pin_status_label.setText("✗ No PIN configured")
            self.pin_status_label.setStyleSheet("color: red;")
            self.remove_pin_btn.setEnabled(False)

        # Require PIN on start
        self.require_pin_check.setChecked(
            self.auth_manager.is_pin_required_on_start()
        )

        # Auto-lock
        self.autolock_enabled.setChecked(
            self.auth_manager.is_auto_lock_enabled()
        )
        self.autolock_spin.setValue(
            self.auth_manager.get_auto_lock_minutes()
        )

    def _on_set_pin_clicked(self):
        """Handle set PIN button."""
        from .lock_screen import SetupPinDialog

        dialog = SetupPinDialog(self)
        if dialog.exec():
            pin = dialog.get_pin()
            if pin:
                self.auth_manager.set_pin(pin)
                self._load_settings()
                QMessageBox.information(
                    self,
                    "Success",
                    "PIN configured successfully"
                )

    def _on_remove_pin_clicked(self):
        """Handle remove PIN button."""
        reply = QMessageBox.question(
            self,
            "Remove PIN",
            "Are you sure you want to remove PIN protection?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.auth_manager.config['pin_hash'] = None
            self.auth_manager._save_config()
            self.auth_manager.log_security_event('pin_removed', {})
            self._load_settings()

    def _on_settings_changed(self):
        """Handle settings change."""
        pass  # Enable save button if needed

    def _on_save_clicked(self):
        """Save settings."""
        # Auto-lock
        self.auth_manager.set_auto_lock(
            self.autolock_enabled.isChecked(),
            self.autolock_spin.value()
        )

        # Require PIN on start
        self.auth_manager.set_require_pin_on_start(
            self.require_pin_check.isChecked()
        )

        self.settings_changed.emit()

        QMessageBox.information(
            self,
            "Success",
            "Security settings saved"
        )
