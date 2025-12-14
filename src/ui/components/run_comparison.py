"""
Run comparison widget for side-by-side analysis.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QPushButton,
    QComboBox, QSplitter, QTextEdit, QHeaderView
)
from PySide6.QtCore import Qt, Signal
from typing import Dict, Any, List, Optional
import json
from datetime import datetime


class RunComparisonWidget(QWidget):
    """
    Side-by-side comparison of two execution runs.

    Compares:
    - Execution metadata (duration, status, timestamps)
    - Step-by-step results
    - Output data diffs
    - Performance metrics
    - Error messages
    """

    comparison_requested = Signal(str, str)  # run_id_1, run_id_2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.run1_data: Optional[Dict[str, Any]] = None
        self.run2_data: Optional[Dict[str, Any]] = None

        self._init_ui()

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)

        # Selection section
        selection_layout = QHBoxLayout()

        # Run 1 selector
        selection_layout.addWidget(QLabel("Run 1:"))
        self.run1_combo = QComboBox()
        self.run1_combo.currentTextChanged.connect(self._on_run1_selected)
        selection_layout.addWidget(self.run1_combo)

        # Run 2 selector
        selection_layout.addWidget(QLabel("Run 2:"))
        self.run2_combo = QComboBox()
        self.run2_combo.currentTextChanged.connect(self._on_run2_selected)
        selection_layout.addWidget(self.run2_combo)

        # Compare button
        self.compare_btn = QPushButton("Compare")
        self.compare_btn.clicked.connect(self._on_compare_clicked)
        selection_layout.addWidget(self.compare_btn)

        selection_layout.addStretch()
        layout.addLayout(selection_layout)

        # Splitter for side-by-side view
        splitter = QSplitter(Qt.Vertical)

        # Metadata comparison
        self.metadata_table = QTableWidget()
        self.metadata_table.setColumnCount(3)
        self.metadata_table.setHorizontalHeaderLabels(["Metric", "Run 1", "Run 2"])
        self.metadata_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        splitter.addWidget(self._create_section("Metadata Comparison", self.metadata_table))

        # Step comparison
        self.steps_table = QTableWidget()
        self.steps_table.setColumnCount(4)
        self.steps_table.setHorizontalHeaderLabels(["Step", "Run 1 Status", "Run 2 Status", "Difference"])
        self.steps_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        splitter.addWidget(self._create_section("Step Comparison", self.steps_table))

        # Output diff
        self.output_diff = QTextEdit()
        self.output_diff.setReadOnly(True)
        self.output_diff.setFontFamily("Courier")
        splitter.addWidget(self._create_section("Output Diff", self.output_diff))

        layout.addWidget(splitter)

    def _create_section(self, title: str, widget: QWidget) -> QWidget:
        """Create labeled section."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(f"<b>{title}</b>")
        layout.addWidget(label)
        layout.addWidget(widget)

        return container

    def set_available_runs(self, runs: List[Dict[str, Any]]):
        """
        Set list of available runs.

        Args:
            runs: List of run metadata dicts with 'run_id', 'pipeline_id', 'started_at'
        """
        self.run1_combo.clear()
        self.run2_combo.clear()

        for run in runs:
            display_text = f"{run['run_id']} - {run['pipeline_id']} ({run['started_at']})"
            self.run1_combo.addItem(display_text, run['run_id'])
            self.run2_combo.addItem(display_text, run['run_id'])

    def _on_run1_selected(self, text: str):
        """Handle run 1 selection."""
        if text:
            self.run1_data = None  # Will be loaded on compare

    def _on_run2_selected(self, text: str):
        """Handle run 2 selection."""
        if text:
            self.run2_data = None  # Will be loaded on compare

    def _on_compare_clicked(self):
        """Handle compare button click."""
        run1_id = self.run1_combo.currentData()
        run2_id = self.run2_combo.currentData()

        if run1_id and run2_id:
            self.comparison_requested.emit(run1_id, run2_id)

    def set_comparison_data(self, run1: Dict[str, Any], run2: Dict[str, Any]):
        """
        Set data for comparison.

        Args:
            run1: First run data
            run2: Second run data
        """
        self.run1_data = run1
        self.run2_data = run2

        self._populate_metadata_comparison()
        self._populate_steps_comparison()
        self._populate_output_diff()

    def _populate_metadata_comparison(self):
        """Populate metadata comparison table."""
        if not self.run1_data or not self.run2_data:
            return

        metrics = [
            ("Run ID", "run_id"),
            ("Pipeline ID", "pipeline_id"),
            ("Source", "source"),
            ("Status", "state"),
            ("Started At", "started_at"),
            ("Finished At", "finished_at"),
            ("Duration (s)", "duration_seconds"),
            ("Progress", "progress"),
            ("Steps Completed", "completed_steps"),
            ("Total Steps", "total_steps"),
            ("Error", "error"),
        ]

        self.metadata_table.setRowCount(len(metrics))

        for row, (label, key) in enumerate(metrics):
            # Metric name
            self.metadata_table.setItem(row, 0, QTableWidgetItem(label))

            # Run 1 value
            val1 = self.run1_data.get(key, "N/A")
            item1 = QTableWidgetItem(str(val1))
            self.metadata_table.setItem(row, 1, item1)

            # Run 2 value
            val2 = self.run2_data.get(key, "N/A")
            item2 = QTableWidgetItem(str(val2))
            self.metadata_table.setItem(row, 2, item2)

            # Highlight differences
            if val1 != val2:
                item1.setBackground(Qt.yellow)
                item2.setBackground(Qt.yellow)

    def _populate_steps_comparison(self):
        """Populate step-by-step comparison."""
        if not self.run1_data or not self.run2_data:
            return

        steps1 = self.run1_data.get('completed_step_ids', [])
        steps2 = self.run2_data.get('completed_step_ids', [])

        all_steps = sorted(set(steps1 + steps2))

        self.steps_table.setRowCount(len(all_steps))

        for row, step in enumerate(all_steps):
            # Step name
            self.steps_table.setItem(row, 0, QTableWidgetItem(step))

            # Run 1 status
            status1 = "✓ Completed" if step in steps1 else "✗ Not Run"
            item1 = QTableWidgetItem(status1)
            if step not in steps1:
                item1.setBackground(Qt.red)
            self.steps_table.setItem(row, 1, item1)

            # Run 2 status
            status2 = "✓ Completed" if step in steps2 else "✗ Not Run"
            item2 = QTableWidgetItem(status2)
            if step not in steps2:
                item2.setBackground(Qt.red)
            self.steps_table.setItem(row, 2, item2)

            # Difference
            if (step in steps1) != (step in steps2):
                diff = "Different"
                diff_item = QTableWidgetItem(diff)
                diff_item.setBackground(Qt.yellow)
                self.steps_table.setItem(row, 3, diff_item)
            else:
                self.steps_table.setItem(row, 3, QTableWidgetItem("Same"))

    def _populate_output_diff(self):
        """Populate output diff view."""
        if not self.run1_data or not self.run2_data:
            return

        # Get output data if available
        output1 = self.run1_data.get('output_data', {})
        output2 = self.run2_data.get('output_data', {})

        diff_lines = []
        diff_lines.append("=" * 80)
        diff_lines.append("OUTPUT COMPARISON")
        diff_lines.append("=" * 80)
        diff_lines.append("")

        # Compare keys
        keys1 = set(output1.keys())
        keys2 = set(output2.keys())

        only_in_1 = keys1 - keys2
        only_in_2 = keys2 - keys1
        common = keys1 & keys2

        if only_in_1:
            diff_lines.append(f"[ONLY IN RUN 1] {len(only_in_1)} keys:")
            for key in sorted(only_in_1):
                diff_lines.append(f"  - {key}: {self._format_value(output1[key])}")
            diff_lines.append("")

        if only_in_2:
            diff_lines.append(f"[ONLY IN RUN 2] {len(only_in_2)} keys:")
            for key in sorted(only_in_2):
                diff_lines.append(f"  + {key}: {self._format_value(output2[key])}")
            diff_lines.append("")

        if common:
            diff_lines.append(f"[COMMON KEYS] {len(common)} keys:")
            for key in sorted(common):
                val1 = output1[key]
                val2 = output2[key]

                if val1 == val2:
                    diff_lines.append(f"  = {key}: {self._format_value(val1)}")
                else:
                    diff_lines.append(f"  ! {key}:")
                    diff_lines.append(f"      Run 1: {self._format_value(val1)}")
                    diff_lines.append(f"      Run 2: {self._format_value(val2)}")
            diff_lines.append("")

        # Performance comparison
        if 'duration_seconds' in self.run1_data and 'duration_seconds' in self.run2_data:
            dur1 = self.run1_data['duration_seconds']
            dur2 = self.run2_data['duration_seconds']
            diff_pct = ((dur2 - dur1) / dur1 * 100) if dur1 > 0 else 0

            diff_lines.append("=" * 80)
            diff_lines.append("PERFORMANCE COMPARISON")
            diff_lines.append("=" * 80)
            diff_lines.append(f"Run 1 Duration: {dur1:.2f}s")
            diff_lines.append(f"Run 2 Duration: {dur2:.2f}s")
            diff_lines.append(f"Difference: {diff_pct:+.2f}%")

        self.output_diff.setPlainText("\n".join(diff_lines))

    def _format_value(self, value: Any) -> str:
        """Format value for display."""
        if isinstance(value, (dict, list)):
            return json.dumps(value, indent=2)[:100] + "..."
        return str(value)[:100]


class RunHistoryWidget(QWidget):
    """
    Run history browser with filtering and search.
    """

    run_selected = Signal(str)  # run_id
    comparison_requested = Signal(str, str)  # run_id_1, run_id_2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.runs: List[Dict[str, Any]] = []
        self.selected_runs: List[str] = []

        self._init_ui()

    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)

        # Filter section
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Pipeline:"))
        self.pipeline_filter = QComboBox()
        self.pipeline_filter.addItem("All")
        self.pipeline_filter.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.pipeline_filter)

        filter_layout.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItem("All")
        self.status_filter.addItems(["COMPLETED", "FAILED", "RUNNING", "PAUSED", "STOPPED"])
        self.status_filter.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.status_filter)

        filter_layout.addStretch()

        self.compare_btn = QPushButton("Compare Selected")
        self.compare_btn.clicked.connect(self._on_compare_clicked)
        self.compare_btn.setEnabled(False)
        filter_layout.addWidget(self.compare_btn)

        layout.addLayout(filter_layout)

        # History table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Run ID", "Pipeline", "Source", "Status",
            "Started", "Duration", "Progress"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)

        layout.addWidget(self.table)

    def set_runs(self, runs: List[Dict[str, Any]]):
        """
        Set run history data.

        Args:
            runs: List of run metadata dicts
        """
        self.runs = runs

        # Update pipeline filter
        pipelines = set(run.get('pipeline_id', '') for run in runs)
        current = self.pipeline_filter.currentText()
        self.pipeline_filter.clear()
        self.pipeline_filter.addItem("All")
        self.pipeline_filter.addItems(sorted(pipelines))
        if current in pipelines:
            self.pipeline_filter.setCurrentText(current)

        self._apply_filters()

    def _apply_filters(self):
        """Apply current filters to table."""
        pipeline_filter = self.pipeline_filter.currentText()
        status_filter = self.status_filter.currentText()

        filtered = []
        for run in self.runs:
            if pipeline_filter != "All" and run.get('pipeline_id') != pipeline_filter:
                continue
            if status_filter != "All" and run.get('state') != status_filter:
                continue
            filtered.append(run)

        self._populate_table(filtered)

    def _populate_table(self, runs: List[Dict[str, Any]]):
        """Populate table with runs."""
        self.table.setRowCount(len(runs))

        for row, run in enumerate(runs):
            # Run ID
            self.table.setItem(row, 0, QTableWidgetItem(run.get('run_id', '')))

            # Pipeline
            self.table.setItem(row, 1, QTableWidgetItem(run.get('pipeline_id', '')))

            # Source
            self.table.setItem(row, 2, QTableWidgetItem(run.get('source', '')))

            # Status
            status = run.get('state', '')
            status_item = QTableWidgetItem(status)
            if status == 'COMPLETED':
                status_item.setBackground(Qt.green)
            elif status == 'FAILED':
                status_item.setBackground(Qt.red)
            elif status == 'RUNNING':
                status_item.setBackground(Qt.yellow)
            self.table.setItem(row, 3, status_item)

            # Started
            self.table.setItem(row, 4, QTableWidgetItem(run.get('started_at', '')))

            # Duration
            duration = run.get('duration_seconds', 0)
            self.table.setItem(row, 5, QTableWidgetItem(f"{duration:.2f}s"))

            # Progress
            progress = run.get('progress', 0)
            self.table.setItem(row, 6, QTableWidgetItem(f"{progress * 100:.1f}%"))

    def _on_selection_changed(self):
        """Handle selection changes."""
        selected_rows = self.table.selectionModel().selectedRows()
        self.selected_runs = [
            self.table.item(row.row(), 0).text()
            for row in selected_rows
        ]

        self.compare_btn.setEnabled(len(self.selected_runs) == 2)

    def _on_row_double_clicked(self, row: int, col: int):
        """Handle row double-click."""
        run_id = self.table.item(row, 0).text()
        self.run_selected.emit(run_id)

    def _on_compare_clicked(self):
        """Handle compare button click."""
        if len(self.selected_runs) == 2:
            self.comparison_requested.emit(self.selected_runs[0], self.selected_runs[1])
