"""
Diagnostics export dialog for the UI.

Provides a user-friendly interface for exporting platform diagnostics.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.common.logging_utils import get_logger
from src.devtools.diagnostics_exporter import DiagnosticsExporter

log = get_logger("ui.diagnostics_dialog")


class DiagnosticsExportThread(QThread):
    """Background thread for exporting diagnostics."""

    progress = Signal(str)  # Progress message
    finished = Signal(str, bool)  # (output_path, success)
    error = Signal(str)  # Error message

    def __init__(
        self,
        output_path: Path,
        format: str,
        run_id: Optional[str] = None,
    ):
        super().__init__()
        self.output_path = output_path
        self.format = format
        self.run_id = run_id

    def run(self) -> None:
        """Export diagnostics in background thread."""
        try:
            self.progress.emit("Initializing diagnostics exporter...")

            exporter = DiagnosticsExporter(
                output_path=self.output_path,
                format=self.format,
                run_id=self.run_id,
            )

            self.progress.emit("Collecting system information...")
            exporter._collect_system_info()

            self.progress.emit("Collecting platform configuration...")
            exporter._collect_platform_info()

            self.progress.emit("Collecting database diagnostics...")
            exporter._collect_database_info()

            self.progress.emit("Collecting run history...")
            exporter._collect_run_history()

            self.progress.emit("Collecting logs...")
            exporter._collect_logs()

            self.progress.emit("Collecting environment variables...")
            exporter._collect_environment()

            self.progress.emit("Collecting installed packages...")
            exporter._collect_installed_packages()

            self.progress.emit("Collecting performance metrics...")
            exporter._collect_performance_metrics()

            self.progress.emit("Collecting recent errors...")
            exporter._collect_recent_errors()

            self.progress.emit(f"Exporting as {self.format.upper()}...")
            output_file = exporter.export()

            self.progress.emit("Export complete!")
            self.finished.emit(str(output_file.absolute()), True)

        except Exception as e:
            log.error(f"Diagnostics export failed: {e}", exc_info=True)
            self.error.emit(str(e))
            self.finished.emit("", False)


class DiagnosticsDialog(QDialog):
    """Dialog for exporting platform diagnostics."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Export Diagnostics")
        self.setModal(True)
        self.resize(600, 500)

        self.export_thread: Optional[DiagnosticsExportThread] = None
        self.output_path: Optional[Path] = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        header = QLabel("Export Platform Diagnostics")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        description = QLabel(
            "Export comprehensive diagnostics including system information, "
            "run history, logs, configuration, and performance metrics. "
            "All sensitive data (passwords, tokens, keys) will be automatically redacted."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #666;")
        layout.addWidget(description)

        # Format selection
        format_group = QGroupBox("Export Format")
        format_layout = QVBoxLayout(format_group)

        self.format_buttons = QButtonGroup(self)

        self.zip_radio = QRadioButton("ZIP Bundle (recommended)")
        self.zip_radio.setChecked(True)
        self.zip_radio.setToolTip(
            "Exports as a ZIP archive containing JSON data, HTML report, and log files"
        )
        self.format_buttons.addButton(self.zip_radio, 0)
        format_layout.addWidget(self.zip_radio)

        self.json_radio = QRadioButton("JSON")
        self.json_radio.setToolTip("Exports as a single JSON file for programmatic access")
        self.format_buttons.addButton(self.json_radio, 1)
        format_layout.addWidget(self.json_radio)

        self.html_radio = QRadioButton("HTML Report")
        self.html_radio.setToolTip("Exports as a human-readable HTML report")
        self.format_buttons.addButton(self.html_radio, 2)
        format_layout.addWidget(self.html_radio)

        layout.addWidget(format_group)

        # Run ID filter (optional)
        filter_group = QGroupBox("Optional Filters")
        filter_layout = QVBoxLayout(filter_group)

        run_id_layout = QHBoxLayout()
        run_id_layout.addWidget(QLabel("Run ID:"))

        self.run_id_input = QLineEdit()
        self.run_id_input.setPlaceholderText("Leave empty to include all runs")
        self.run_id_input.setToolTip(
            "Enter a specific Run ID to export diagnostics for that run only"
        )
        run_id_layout.addWidget(self.run_id_input)

        filter_layout.addLayout(run_id_layout)
        layout.addWidget(filter_group)

        # Output path
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout(output_group)

        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Save to:"))

        self.output_path_input = QLineEdit()
        self.output_path_input.setReadOnly(True)
        path_layout.addWidget(self.output_path_input)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_output_path)
        path_layout.addWidget(browse_btn)

        output_layout.addLayout(path_layout)
        layout.addWidget(output_group)

        # Progress section
        self.progress_group = QGroupBox("Export Progress")
        self.progress_group.setVisible(False)
        progress_layout = QVBoxLayout(self.progress_group)

        self.progress_label = QLabel("Preparing export...")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        progress_layout.addWidget(self.progress_bar)

        layout.addWidget(self.progress_group)

        # Status/Info text
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(100)
        self.status_text.setVisible(False)
        layout.addWidget(self.status_text)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.export_btn = QPushButton("Export")
        self.export_btn.setDefault(True)
        self.export_btn.clicked.connect(self._start_export)
        button_layout.addWidget(self.export_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

        # Set default output path
        self._update_default_output_path()

        # Connect format change to update output path
        self.format_buttons.buttonClicked.connect(self._update_default_output_path)

    def _get_format_extension(self) -> str:
        """Get file extension for selected format."""
        if self.json_radio.isChecked():
            return "json"
        elif self.html_radio.isChecked():
            return "html"
        else:
            return "zip"

    def _update_default_output_path(self) -> None:
        """Update the default output path based on selected format."""
        if not self.output_path_input.text():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            extension = self._get_format_extension()
            default_path = Path.cwd() / f"diagnostics_{timestamp}.{extension}"
            self.output_path_input.setText(str(default_path))
            self.output_path = default_path

    def _browse_output_path(self) -> None:
        """Open file dialog to select output path."""
        extension = self._get_format_extension()

        if extension == "zip":
            file_filter = "ZIP Archives (*.zip)"
            default_name = "diagnostics.zip"
        elif extension == "json":
            file_filter = "JSON Files (*.json)"
            default_name = "diagnostics.json"
        else:  # html
            file_filter = "HTML Files (*.html)"
            default_name = "diagnostics.html"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Diagnostics Export",
            str(Path.cwd() / default_name),
            file_filter,
        )

        if file_path:
            self.output_path = Path(file_path)
            self.output_path_input.setText(str(self.output_path))

    def _start_export(self) -> None:
        """Start the diagnostics export in background thread."""
        # Validate output path
        if not self.output_path_input.text():
            QMessageBox.warning(
                self,
                "No Output Path",
                "Please select an output path for the diagnostics export.",
            )
            return

        output_path = Path(self.output_path_input.text())

        # Check if file exists
        if output_path.exists():
            reply = QMessageBox.question(
                self,
                "File Exists",
                f"The file '{output_path.name}' already exists. Do you want to overwrite it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )

            if reply == QMessageBox.No:
                return

        # Get format
        format_str = self._get_format_extension()

        # Get run ID filter (if any)
        run_id = self.run_id_input.text().strip() or None

        # Disable controls during export
        self.export_btn.setEnabled(False)
        self.run_id_input.setEnabled(False)
        self.output_path_input.setEnabled(False)
        self.findChild(QPushButton, "Browse...").setEnabled(False)

        for button in self.format_buttons.buttons():
            button.setEnabled(False)

        # Show progress
        self.progress_group.setVisible(True)
        self.status_text.setVisible(True)
        self.status_text.clear()

        # Create and start export thread
        self.export_thread = DiagnosticsExportThread(
            output_path=output_path,
            format=format_str,
            run_id=run_id,
        )

        self.export_thread.progress.connect(self._on_progress)
        self.export_thread.finished.connect(self._on_export_finished)
        self.export_thread.error.connect(self._on_export_error)

        self.export_thread.start()

        log.info("Started diagnostics export", extra={
            "output_path": str(output_path),
            "format": format_str,
            "run_id": run_id,
        })

    def _on_progress(self, message: str) -> None:
        """Handle progress update from export thread."""
        self.progress_label.setText(message)
        self.status_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

        # Scroll to bottom
        cursor = self.status_text.textCursor()
        cursor.movePosition(cursor.End)
        self.status_text.setTextCursor(cursor)

    def _on_export_finished(self, output_path: str, success: bool) -> None:
        """Handle export completion."""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)

        if success and output_path:
            output_file = Path(output_path)
            size_mb = output_file.stat().st_size / (1024**2)

            message = (
                f"Diagnostics exported successfully!\n\n"
                f"File: {output_file.name}\n"
                f"Location: {output_file.parent}\n"
                f"Size: {size_mb:.2f} MB\n\n"
                f"Would you like to open the containing folder?"
            )

            reply = QMessageBox.question(
                self,
                "Export Complete",
                message,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )

            if reply == QMessageBox.Yes:
                # Open folder containing the export
                from src.ui.path_utils import open_parent_folder
                open_parent_folder(str(output_file))

            self.accept()

        else:
            QMessageBox.critical(
                self,
                "Export Failed",
                "Failed to export diagnostics. Check the status log for details.",
            )

            # Re-enable controls
            self.export_btn.setEnabled(True)
            self.run_id_input.setEnabled(True)
            self.output_path_input.setEnabled(True)

            for button in self.format_buttons.buttons():
                button.setEnabled(True)

    def _on_export_error(self, error_msg: str) -> None:
        """Handle export error."""
        self.status_text.append(f"[ERROR] {error_msg}")
        log.error(f"Diagnostics export error: {error_msg}")
