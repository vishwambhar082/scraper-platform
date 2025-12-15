"""
Pipeline Execution Viewer Component.

Provides real-time visualization of pipeline execution including:
- Step-by-step progress tracking
- DAG visualization integration
- Execution state monitoring
- Step timing and status
"""

from __future__ import annotations

from typing import Any, List, Optional

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QLabel,
    QTabWidget,
    QTextEdit,
)

from src.common.logging_utils import get_logger
from src.scheduler import scheduler_db_adapter as run_db
from src.ui.workflow_graph import WorkflowGraphWidget

log = get_logger("ui.components.pipeline_viewer")


class PipelineViewer(QWidget):
    """
    Pipeline execution viewer showing real-time pipeline progress.

    Features:
    - Tree view of pipeline steps with status
    - DAG visualization
    - Step timing information
    - Detailed step output

    Signals:
        step_selected: Emitted when a step is selected (step_name)
    """

    step_selected = Signal(str)  # step_name

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.current_run_id: Optional[str] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Header
        header = QHBoxLayout()
        title = QLabel("Pipeline Execution")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #1f2937;")
        header.addWidget(title)
        header.addStretch()

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        refresh_btn.setStyleSheet("""
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
        header.addWidget(refresh_btn)

        layout.addLayout(header)

        # Tabs for different views
        tabs = QTabWidget()

        # Steps tree view
        steps_tab = self._create_steps_tab()
        tabs.addTab(steps_tab, "Steps")

        # Workflow graph view
        graph_tab = self._create_graph_tab()
        tabs.addTab(graph_tab, "DAG Visualization")

        layout.addWidget(tabs, 1)

    def _create_steps_tab(self) -> QWidget:
        """Create the steps tree view tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Steps tree
        self.steps_tree = QTreeWidget()
        self.steps_tree.setHeaderLabels(["Step", "Status", "Duration (s)", "Output"])
        self.steps_tree.setColumnWidth(0, 250)
        self.steps_tree.setColumnWidth(1, 100)
        self.steps_tree.setColumnWidth(2, 100)
        self.steps_tree.setAlternatingRowColors(True)
        self.steps_tree.itemSelectionChanged.connect(self._on_step_selected)
        self.steps_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #e5e7eb;
                border-radius: 4px;
                background-color: white;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QHeaderView::section {
                background-color: #f3f4f6;
                padding: 8px;
                border: 1px solid #e5e7eb;
                font-weight: 600;
            }
        """)
        layout.addWidget(self.steps_tree, 1)

        # Step details section
        details_label = QLabel("Step Details")
        details_label.setStyleSheet("font-weight: bold; font-size: 12px; margin-top: 8px;")
        layout.addWidget(details_label)

        self.step_details = QTextEdit()
        self.step_details.setReadOnly(True)
        self.step_details.setMaximumHeight(150)
        self.step_details.setPlaceholderText("Select a step to view details")
        self.step_details.setStyleSheet("""
            QTextEdit {
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.step_details)

        return widget

    def _create_graph_tab(self) -> QWidget:
        """Create the DAG visualization tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Controls
        controls = QHBoxLayout()

        zoom_in_btn = QPushButton("Zoom In")
        zoom_in_btn.clicked.connect(self._zoom_in)
        controls.addWidget(zoom_in_btn)

        zoom_out_btn = QPushButton("Zoom Out")
        zoom_out_btn.clicked.connect(self._zoom_out)
        controls.addWidget(zoom_out_btn)

        controls.addStretch()

        layout.addLayout(controls)

        # Workflow graph widget
        self.workflow_graph = WorkflowGraphWidget()
        layout.addWidget(self.workflow_graph, 1)

        return widget

    def _on_step_selected(self) -> None:
        """Handle step selection."""
        items = self.steps_tree.selectedItems()
        if items:
            step_name = items[0].text(0)
            self.step_selected.emit(step_name)
            self._load_step_details(step_name)

    def _load_step_details(self, step_name: str) -> None:
        """Load details for the selected step."""
        if not self.current_run_id:
            self.step_details.setPlainText("No run loaded")
            return

        try:
            steps = run_db.fetch_run_steps(self.current_run_id)
            step = next((s for s in steps if s.name == step_name), None)

            if not step:
                self.step_details.setPlainText(f"Step '{step_name}' not found")
                return

            details = [
                f"Step: {step.name}",
                f"Status: {step.status}",
                f"Started: {step.started_at}",
                f"Finished: {step.finished_at}",
                f"Duration: {step.duration_seconds:.2f}s" if step.duration_seconds else "Duration: -",
            ]

            # Add metadata if available
            if hasattr(step, 'metadata') and step.metadata:
                details.append("\nMetadata:")
                for key, value in step.metadata.items():
                    details.append(f"  {key}: {value}")

            self.step_details.setPlainText("\n".join(details))

        except Exception as e:
            log.error(f"Failed to load step details: {e}")
            self.step_details.setPlainText(f"Error loading details: {e}")

    def _zoom_in(self) -> None:
        """Zoom in the workflow graph."""
        if hasattr(self.workflow_graph, 'zoom_in'):
            self.workflow_graph.zoom_in()

    def _zoom_out(self) -> None:
        """Zoom out the workflow graph."""
        if hasattr(self.workflow_graph, 'zoom_out'):
            self.workflow_graph.zoom_out()

    def load_run(self, run_id: str) -> None:
        """Load a pipeline run for visualization."""
        self.current_run_id = run_id
        self.refresh()

    def refresh(self) -> None:
        """Refresh the pipeline view."""
        if not self.current_run_id:
            self.steps_tree.clear()
            self.step_details.clear()
            return

        try:
            steps = run_db.fetch_run_steps(self.current_run_id)
            self._populate_steps_tree(steps)
        except Exception as e:
            log.error(f"Failed to refresh pipeline view: {e}")

    def _populate_steps_tree(self, steps: List[Any]) -> None:
        """Populate the steps tree with run steps."""
        self.steps_tree.clear()

        for step in steps:
            duration = f"{step.duration_seconds:.2f}" if step.duration_seconds else "-"
            item = QTreeWidgetItem([
                step.name,
                step.status,
                duration,
                ""
            ])

            # Color code based on status
            if step.status == "failed":
                item.setForeground(0, QColor("#ef4444"))
                item.setForeground(1, QColor("#ef4444"))
            elif step.status == "success":
                item.setForeground(1, QColor("#10b981"))
            elif step.status == "running":
                item.setForeground(1, QColor("#3b82f6"))

            self.steps_tree.addTopLevelItem(item)

    def update_step_status(self, step_id: str, status: str) -> None:
        """Update the status of a step in real-time."""
        for i in range(self.steps_tree.topLevelItemCount()):
            item = self.steps_tree.topLevelItem(i)
            if item.text(0) == step_id:
                item.setText(1, status)

                # Update color
                if status == "failed":
                    item.setForeground(1, QColor("#ef4444"))
                elif status == "success":
                    item.setForeground(1, QColor("#10b981"))
                elif status == "running":
                    item.setForeground(1, QColor("#3b82f6"))
                break

    def clear(self) -> None:
        """Clear the pipeline viewer."""
        self.current_run_id = None
        self.steps_tree.clear()
        self.step_details.clear()
