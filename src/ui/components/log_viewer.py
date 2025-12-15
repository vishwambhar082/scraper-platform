"""
Log Viewer Component.

Provides a comprehensive log display with filtering capabilities:
- Live log streaming
- Search/filter functionality
- Log level filtering
- Export capabilities
- Auto-scroll option
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QComboBox,
    QLineEdit,
    QLabel,
    QCheckBox,
    QFileDialog,
    QMessageBox,
)

from src.common.logging_utils import get_logger

log = get_logger("ui.components.log_viewer")


class LogViewer(QWidget):
    """
    Log viewer component with filtering and export capabilities.

    Features:
    - Live log streaming
    - Search filter
    - Log level filter
    - Export to file
    - Auto-scroll toggle
    - Persistent log storage

    Signals:
        logs_exported: Emitted when logs are exported (filename)
    """

    logs_exported = Signal(str)  # filename

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.log_buffer: List[Dict[str, Any]] = []
        self.log_file_path = Path("logs/ui_logs.json")
        self.autoscroll = True
        self._setup_ui()
        self._load_persisted_logs()

    def _setup_ui(self) -> None:
        """Setup the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Filter toolbar
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(6)

        # Search box
        self.search_filter = QLineEdit()
        self.search_filter.setPlaceholderText("Search logs...")
        self.search_filter.textChanged.connect(self._apply_filters)
        self.search_filter.setMaximumWidth(200)
        filter_layout.addWidget(self.search_filter)

        # Level filter
        self.level_filter = QComboBox()
        self.level_filter.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_filter.currentTextChanged.connect(self._apply_filters)
        self.level_filter.setMaximumWidth(120)
        filter_layout.addWidget(self.level_filter)

        # Module filter (optional)
        self.module_filter = QLineEdit()
        self.module_filter.setPlaceholderText("Module filter...")
        self.module_filter.textChanged.connect(self._apply_filters)
        self.module_filter.setMaximumWidth(150)
        filter_layout.addWidget(self.module_filter)

        filter_layout.addStretch()

        # Auto-scroll checkbox
        self.autoscroll_cb = QCheckBox("Auto-scroll")
        self.autoscroll_cb.setChecked(True)
        self.autoscroll_cb.stateChanged.connect(self._toggle_autoscroll)
        filter_layout.addWidget(self.autoscroll_cb)

        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear)
        clear_btn.setMaximumWidth(80)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #6b7280;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
        """)
        filter_layout.addWidget(clear_btn)

        # Export button
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self.export_logs)
        export_btn.setMaximumWidth(80)
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        filter_layout.addWidget(export_btn)

        layout.addLayout(filter_layout)

        # Logs text area
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setStyleSheet("""
            QTextEdit {
                background-color: #000000;
                color: #00ff00;
                border: 1px solid #333333;
                border-radius: 4px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                padding: 8px;
                selection-background-color: #444444;
                selection-color: #00ff00;
            }
        """)
        layout.addWidget(self.logs_text, 1)

        # Status bar
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Logs: 0 entries")
        self.status_label.setStyleSheet("color: #6b7280; font-size: 10px;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)

    def _toggle_autoscroll(self, state: int) -> None:
        """Toggle auto-scroll."""
        self.autoscroll = (state == Qt.Checked)

    def append_log(self, level: str, message: str, module: str = "") -> None:
        """
        Append a log message.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            module: Module name (optional)
        """
        timestamp = datetime.utcnow()
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "module": module,
            "text": f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] [{level}] {message}"
        }

        self.log_buffer.append(log_entry)

        # Keep buffer size manageable
        if len(self.log_buffer) > 10000:
            self.log_buffer = self.log_buffer[-5000:]

        # Save to disk periodically
        if len(self.log_buffer) % 10 == 0:
            self._save_persisted_logs()

        # Update display
        self._apply_filters()

    def _apply_filters(self) -> None:
        """Apply search and level filters to log display."""
        search_text = self.search_filter.text().lower()
        level_filter = self.level_filter.currentText()
        module_filter = self.module_filter.text().strip().lower()

        filtered_logs = []
        for entry in self.log_buffer:
            text = entry.get("text", "")
            entry_level = entry.get("level", "")
            entry_module = entry.get("module", "").lower()

            # Filter by level
            if level_filter != "ALL" and entry_level != level_filter:
                continue

            # Filter by search text
            if search_text and search_text not in text.lower():
                continue

            # Filter by module
            if module_filter and module_filter not in entry_module:
                continue

            filtered_logs.append(text)

        # Update display
        self.logs_text.setPlainText("\n".join(filtered_logs))

        # Update status
        self.status_label.setText(
            f"Logs: {len(filtered_logs)} of {len(self.log_buffer)} entries"
        )

        # Auto-scroll to bottom
        if self.autoscroll:
            scrollbar = self.logs_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def clear(self) -> None:
        """Clear all logs."""
        reply = QMessageBox.question(
            self,
            "Clear Logs",
            "Are you sure you want to clear all logs?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.log_buffer.clear()
            self.logs_text.clear()
            self.status_label.setText("Logs: 0 entries")

    def export_logs(self) -> None:
        """Export logs to a file."""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Logs",
            f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;JSON Files (*.json);;All Files (*)"
        )

        if not filename:
            return

        try:
            if filename.endswith('.json'):
                # Export as JSON
                serializable_logs = []
                for entry in self.log_buffer:
                    log_entry = entry.copy()
                    if isinstance(log_entry.get("timestamp"), datetime):
                        log_entry["timestamp"] = log_entry["timestamp"].isoformat()
                    serializable_logs.append(log_entry)

                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(serializable_logs, f, indent=2)
            else:
                # Export as plain text
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.logs_text.toPlainText())

            self.logs_exported.emit(filename)
            QMessageBox.information(self, "Export Complete", f"Logs exported to:\n{filename}")
            log.info(f"Logs exported to {filename}")

        except Exception as e:
            log.error(f"Failed to export logs: {e}")
            QMessageBox.critical(self, "Export Error", f"Failed to export logs: {e}")

    def _load_persisted_logs(self) -> None:
        """Load persisted logs from disk."""
        if not self.log_file_path.exists():
            return

        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                persisted_logs = json.load(f)

            # Convert timestamp strings back to datetime objects
            for entry in persisted_logs:
                if isinstance(entry.get("timestamp"), str):
                    try:
                        entry["timestamp"] = datetime.fromisoformat(entry["timestamp"])
                    except (ValueError, TypeError):
                        entry["timestamp"] = datetime.utcnow()

            # Keep only recent logs (last 1000 entries)
            self.log_buffer = persisted_logs[-1000:]
            self._apply_filters()

            log.info(f"Loaded {len(self.log_buffer)} persisted log entries")

        except Exception as e:
            log.error(f"Failed to load persisted logs: {e}")
            self.log_buffer = []

    def _save_persisted_logs(self) -> None:
        """Save logs to disk for persistence."""
        try:
            # Ensure logs directory exists
            self.log_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert datetime objects to strings for JSON serialization
            serializable_logs = []
            for entry in self.log_buffer[-1000:]:  # Keep only last 1000 entries
                log_entry = entry.copy()
                if isinstance(log_entry.get("timestamp"), datetime):
                    log_entry["timestamp"] = log_entry["timestamp"].isoformat()
                serializable_logs.append(log_entry)

            with open(self.log_file_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_logs, f, indent=2)

        except Exception as e:
            log.error(f"Failed to save persisted logs: {e}")

    def get_log_count(self) -> int:
        """Get the total number of log entries."""
        return len(self.log_buffer)

    def get_filtered_log_count(self) -> int:
        """Get the number of filtered log entries currently displayed."""
        # This is approximate based on the display text
        return len(self.logs_text.toPlainText().split('\n'))

    def set_log_level_filter(self, level: str) -> None:
        """Programmatically set the log level filter."""
        index = self.level_filter.findText(level)
        if index >= 0:
            self.level_filter.setCurrentIndex(index)
