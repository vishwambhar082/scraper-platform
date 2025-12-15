"""
Settings Editor Component.

Provides a configuration editor for managing environment variables and settings:
- Settings form with validation
- Save/load configuration
- Environment variable management
- Validation feedback
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QLabel,
    QMessageBox,
    QLineEdit,
    QFileDialog,
)

from src.common.logging_utils import get_logger

log = get_logger("ui.components.settings_editor")


class SettingsEditor(QWidget):
    """
    Settings editor component for managing configuration.

    Features:
    - Environment variables table
    - Add/edit/delete variables
    - Validation
    - Save to .env file
    - Load from .env file

    Signals:
        settings_changed: Emitted when settings are modified
        settings_saved: Emitted when settings are saved (filepath)
    """

    settings_changed = Signal()
    settings_saved = Signal(str)  # filepath

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.env_vars: Dict[str, str] = {}
        self._setup_ui()
        self._load_current_env()

    def _setup_ui(self) -> None:
        """Setup the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # Header
        header = QLabel("Settings & Environment Variables")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #1f2937;")
        layout.addWidget(header)

        description = QLabel(
            "Configure environment variables and application settings. "
            "Changes will be saved to the .env file."
        )
        description.setStyleSheet("color: #6b7280; margin-bottom: 8px;")
        description.setWordWrap(True)
        layout.addWidget(description)

        # Toolbar
        toolbar = QHBoxLayout()

        add_btn = QPushButton("Add Variable")
        add_btn.clicked.connect(self._add_variable)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        toolbar.addWidget(add_btn)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_variable)
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """)
        toolbar.addWidget(remove_btn)

        toolbar.addStretch()

        load_btn = QPushButton("Load from File")
        load_btn.clicked.connect(self._load_from_file)
        toolbar.addWidget(load_btn)

        layout.addLayout(toolbar)

        # Settings table
        self.settings_table = self._create_settings_table()
        layout.addWidget(self.settings_table, 1)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        reset_btn = QPushButton("Reset to Current")
        reset_btn.clicked.connect(self._load_current_env)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #6b7280;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
        """)
        button_layout.addWidget(reset_btn)

        save_btn = QPushButton("Save Changes")
        save_btn.clicked.connect(self._save_settings)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _create_settings_table(self) -> QTableWidget:
        """Create the settings table."""
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Variable Name", "Value"])

        # Set column widths
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        table.setColumnWidth(0, 250)

        table.setAlternatingRowColors(True)
        table.itemChanged.connect(self._on_item_changed)
        table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e5e7eb;
                border: 1px solid #e5e7eb;
                border-radius: 4px;
            }
            QHeaderView::section {
                background-color: #f3f4f6;
                padding: 8px;
                border: 1px solid #e5e7eb;
                font-weight: 600;
            }
            QTableWidget::item {
                padding: 8px;
            }
        """)

        return table

    def _load_current_env(self) -> None:
        """Load current environment variables."""
        # Default environment variables
        default_vars = {
            "DB_URL": os.getenv("DB_URL", "sqlite:///./logs/run_db.sqlite"),
            "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "AIRFLOW__DATABASE__SQL_ALCHEMY_CONN": os.getenv("AIRFLOW__DATABASE__SQL_ALCHEMY_CONN", ""),
            "AIRFLOW__CORE__FERNET_KEY": os.getenv("AIRFLOW__CORE__FERNET_KEY", ""),
            "CORS_ORIGINS": os.getenv("CORS_ORIGINS", "http://localhost:3000"),
            "PCID_MASTER_PATH": os.getenv("PCID_MASTER_PATH", "./config/pcid_master.jsonl"),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
            "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
            "MAX_WORKERS": os.getenv("MAX_WORKERS", "4"),
            "PROXY_URL": os.getenv("PROXY_URL", ""),
            "HEADLESS_MODE": os.getenv("HEADLESS_MODE", "True"),
            "SCRAPER_SECRET_KEY": os.getenv("SCRAPER_SECRET_KEY", ""),
            "RUN_DB_PATH": os.getenv("RUN_DB_PATH", ""),
            "SCRAPER_PLATFORM_ENV": os.getenv("SCRAPER_PLATFORM_ENV", os.getenv("ENV", "dev")),
        }

        self.env_vars = default_vars
        self._populate_table()

    def _populate_table(self) -> None:
        """Populate the settings table."""
        self.settings_table.setRowCount(0)
        self.settings_table.setRowCount(len(self.env_vars))

        for i, (key, value) in enumerate(sorted(self.env_vars.items())):
            # Variable name (read-only)
            name_item = QTableWidgetItem(key)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.settings_table.setItem(i, 0, name_item)

            # Value (editable)
            value_item = QTableWidgetItem(value)
            self.settings_table.setItem(i, 1, value_item)

    def _add_variable(self) -> None:
        """Add a new environment variable."""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Add Environment Variable")
        layout = QVBoxLayout(dialog)

        # Name input
        layout.addWidget(QLabel("Variable Name:"))
        name_input = QLineEdit()
        layout.addWidget(name_input)

        # Value input
        layout.addWidget(QLabel("Value:"))
        value_input = QLineEdit()
        layout.addWidget(value_input)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.Accepted:
            var_name = name_input.text().strip()
            var_value = value_input.text().strip()

            if not var_name:
                QMessageBox.warning(self, "Invalid Input", "Variable name cannot be empty")
                return

            if var_name in self.env_vars:
                QMessageBox.warning(self, "Duplicate Variable", f"Variable '{var_name}' already exists")
                return

            self.env_vars[var_name] = var_value
            self._populate_table()
            self.settings_changed.emit()

    def _remove_variable(self) -> None:
        """Remove the selected environment variable."""
        row = self.settings_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a variable to remove")
            return

        var_name = self.settings_table.item(row, 0).text()

        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Are you sure you want to remove '{var_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            del self.env_vars[var_name]
            self._populate_table()
            self.settings_changed.emit()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        """Handle item change in table."""
        if item.column() == 1:  # Value column
            row = item.row()
            var_name = self.settings_table.item(row, 0).text()
            new_value = item.text()
            self.env_vars[var_name] = new_value
            self.settings_changed.emit()

    def _save_settings(self) -> None:
        """Save settings to .env file."""
        env_file = Path(".env")

        try:
            # Create backup if file exists
            if env_file.exists():
                backup_file = env_file.with_suffix('.env.backup')
                backup_file.write_text(env_file.read_text())

            # Write new .env file
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write("# Scraper Platform Environment Configuration\n")
                f.write(f"# Updated: {datetime.now().isoformat()}\n\n")

                for key, value in sorted(self.env_vars.items()):
                    # Escape values with spaces or special characters
                    if ' ' in value or '"' in value:
                        value = f'"{value}"'
                    f.write(f"{key}={value}\n")

            self.settings_saved.emit(str(env_file.absolute()))
            QMessageBox.information(
                self,
                "Settings Saved",
                f"Settings have been saved to {env_file.absolute()}\n\n"
                "Note: You may need to restart the application for changes to take effect."
            )
            log.info(f"Settings saved to {env_file.absolute()}")

        except Exception as e:
            log.error(f"Failed to save settings: {e}")
            QMessageBox.critical(self, "Save Error", f"Failed to save settings: {e}")

    def _load_from_file(self) -> None:
        """Load settings from a .env file."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Environment File",
            ".",
            "Environment Files (*.env);;All Files (*)"
        )

        if not filename:
            return

        try:
            env_vars = {}
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue

                    # Parse KEY=VALUE
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        env_vars[key] = value

            self.env_vars = env_vars
            self._populate_table()
            self.settings_changed.emit()

            QMessageBox.information(
                self,
                "File Loaded",
                f"Loaded {len(env_vars)} environment variables from {filename}"
            )
            log.info(f"Loaded settings from {filename}")

        except Exception as e:
            log.error(f"Failed to load settings from file: {e}")
            QMessageBox.critical(self, "Load Error", f"Failed to load settings: {e}")

    def get_variable(self, key: str) -> Optional[str]:
        """Get the value of an environment variable."""
        return self.env_vars.get(key)

    def set_variable(self, key: str, value: str) -> None:
        """Set an environment variable."""
        self.env_vars[key] = value
        self._populate_table()
        self.settings_changed.emit()

    def get_all_variables(self) -> Dict[str, str]:
        """Get all environment variables."""
        return self.env_vars.copy()
