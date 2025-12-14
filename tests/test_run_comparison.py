"""
Tests for run comparison components.
"""

import pytest
from datetime import datetime
from PySide6.QtWidgets import QApplication
from ui.components.run_comparison import RunComparisonWidget, RunHistoryWidget


@pytest.fixture(scope='session')
def qapp():
    """Create Qt application."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestRunComparisonWidget:
    """Test run comparison widget."""

    @pytest.fixture
    def widget(self, qapp):
        """Create widget."""
        widget = RunComparisonWidget()
        yield widget
        widget.deleteLater()

    def test_init(self, widget):
        """Test initialization."""
        assert widget.run1_data is None
        assert widget.run2_data is None

    def test_set_available_runs(self, widget):
        """Test setting available runs."""
        runs = [
            {
                'run_id': 'run-001',
                'pipeline_id': 'test-pipeline',
                'started_at': '2024-01-01 10:00:00'
            },
            {
                'run_id': 'run-002',
                'pipeline_id': 'test-pipeline',
                'started_at': '2024-01-01 11:00:00'
            }
        ]

        widget.set_available_runs(runs)

        assert widget.run1_combo.count() == 2
        assert widget.run2_combo.count() == 2

    def test_set_comparison_data(self, widget):
        """Test setting comparison data."""
        run1 = {
            'run_id': 'run-001',
            'pipeline_id': 'test-pipeline',
            'state': 'COMPLETED',
            'started_at': '2024-01-01 10:00:00',
            'finished_at': '2024-01-01 10:05:00',
            'duration_seconds': 300,
            'progress': 1.0,
            'completed_steps': 5,
            'total_steps': 5,
            'completed_step_ids': ['step1', 'step2', 'step3'],
            'output_data': {'records': 100}
        }

        run2 = {
            'run_id': 'run-002',
            'pipeline_id': 'test-pipeline',
            'state': 'COMPLETED',
            'started_at': '2024-01-01 11:00:00',
            'finished_at': '2024-01-01 11:06:00',
            'duration_seconds': 360,
            'progress': 1.0,
            'completed_steps': 5,
            'total_steps': 5,
            'completed_step_ids': ['step1', 'step2', 'step3'],
            'output_data': {'records': 120}
        }

        widget.set_comparison_data(run1, run2)

        assert widget.run1_data == run1
        assert widget.run2_data == run2
        assert widget.metadata_table.rowCount() > 0


class TestRunHistoryWidget:
    """Test run history widget."""

    @pytest.fixture
    def widget(self, qapp):
        """Create widget."""
        widget = RunHistoryWidget()
        yield widget
        widget.deleteLater()

    def test_init(self, widget):
        """Test initialization."""
        assert widget.runs == []
        assert widget.selected_runs == []

    def test_set_runs(self, widget):
        """Test setting runs."""
        runs = [
            {
                'run_id': 'run-001',
                'pipeline_id': 'pipeline1',
                'source': 'source1',
                'state': 'COMPLETED',
                'started_at': '2024-01-01 10:00:00',
                'duration_seconds': 300,
                'progress': 1.0
            },
            {
                'run_id': 'run-002',
                'pipeline_id': 'pipeline2',
                'source': 'source2',
                'state': 'FAILED',
                'started_at': '2024-01-01 11:00:00',
                'duration_seconds': 60,
                'progress': 0.3
            }
        ]

        widget.set_runs(runs)

        assert widget.runs == runs
        assert widget.table.rowCount() == 2

    def test_filtering(self, widget):
        """Test run filtering."""
        runs = [
            {
                'run_id': 'run-001',
                'pipeline_id': 'pipeline1',
                'source': 'source1',
                'state': 'COMPLETED',
                'started_at': '2024-01-01 10:00:00',
                'duration_seconds': 300,
                'progress': 1.0
            },
            {
                'run_id': 'run-002',
                'pipeline_id': 'pipeline1',
                'source': 'source1',
                'state': 'FAILED',
                'started_at': '2024-01-01 11:00:00',
                'duration_seconds': 60,
                'progress': 0.3
            },
            {
                'run_id': 'run-003',
                'pipeline_id': 'pipeline2',
                'source': 'source2',
                'state': 'COMPLETED',
                'started_at': '2024-01-01 12:00:00',
                'duration_seconds': 400,
                'progress': 1.0
            }
        ]

        widget.set_runs(runs)

        # Filter by pipeline
        widget.pipeline_filter.setCurrentText('pipeline1')
        widget._apply_filters()
        assert widget.table.rowCount() == 2

        # Filter by status
        widget.status_filter.setCurrentText('COMPLETED')
        widget._apply_filters()
        assert widget.table.rowCount() == 1
