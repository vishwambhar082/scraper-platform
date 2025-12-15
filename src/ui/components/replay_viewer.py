"""
Replay Viewer Component.

Provides session replay controls for debugging and analysis:
- Play/pause/step controls
- Timeline scrubbing
- Speed control
- Breakpoint management
- Event inspection
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QSlider,
    QLabel,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QSplitter,
    QFileDialog,
    QMessageBox,
    QGroupBox,
)

from src.common.logging_utils import get_logger

log = get_logger("ui.components.replay_viewer")


class ReplayViewer(QWidget):
    """
    Session replay viewer for debugging and analysis.

    Features:
    - Play/pause/step controls
    - Timeline navigation with scrubbing
    - Variable speed playback
    - Breakpoints
    - Event inspection
    - Session recording export

    Signals:
        playback_started: Emitted when playback starts
        playback_paused: Emitted when playback pauses
        playback_stopped: Emitted when playback stops
        position_changed: Emitted when position changes (position, total)
        event_selected: Emitted when an event is selected (event_index)
    """

    playback_started = Signal()
    playback_paused = Signal()
    playback_stopped = Signal()
    position_changed = Signal(int, int)  # position, total
    event_selected = Signal(int)  # event_index

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.session_events: List[Dict[str, Any]] = []
        self.current_position = 0
        self.is_playing = False
        self.playback_speed = 1.0
        self.breakpoints: List[int] = []
        self._setup_ui()
        self._setup_playback_timer()

    def _setup_ui(self) -> None:
        """Setup the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("Session Replay")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1f2937;")
        header.addWidget(title)
        header.addStretch()

        # Load session button
        load_btn = QPushButton("Load Session")
        load_btn.clicked.connect(self._load_session)
        load_btn.setStyleSheet("""
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
        header.addWidget(load_btn)

        layout.addLayout(header)

        # Main splitter - events list and details
        splitter = QSplitter(Qt.Horizontal)

        # Left: Events list
        events_widget = self._create_events_widget()
        splitter.addWidget(events_widget)

        # Right: Event details
        details_widget = self._create_details_widget()
        splitter.addWidget(details_widget)

        splitter.setSizes([300, 500])
        layout.addWidget(splitter, 1)

        # Timeline section
        timeline_group = QGroupBox("Timeline")
        timeline_layout = QVBoxLayout(timeline_group)

        # Timeline slider
        slider_layout = QHBoxLayout()
        self.timeline_slider = QSlider(Qt.Horizontal)
        self.timeline_slider.setMinimum(0)
        self.timeline_slider.setMaximum(0)
        self.timeline_slider.valueChanged.connect(self._on_slider_changed)
        slider_layout.addWidget(self.timeline_slider, 1)

        self.position_label = QLabel("0 / 0")
        self.position_label.setStyleSheet("font-family: 'Consolas', monospace;")
        slider_layout.addWidget(self.position_label)

        timeline_layout.addLayout(slider_layout)

        # Playback controls
        controls_layout = QHBoxLayout()

        # Play/Pause button
        self.play_pause_btn = QPushButton("Play")
        self.play_pause_btn.clicked.connect(self._toggle_playback)
        self.play_pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        controls_layout.addWidget(self.play_pause_btn)

        # Stop button
        stop_btn = QPushButton("Stop")
        stop_btn.clicked.connect(self._stop_playback)
        stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """)
        controls_layout.addWidget(stop_btn)

        # Step backward
        step_back_btn = QPushButton("◀ Step")
        step_back_btn.clicked.connect(self._step_backward)
        controls_layout.addWidget(step_back_btn)

        # Step forward
        step_forward_btn = QPushButton("Step ▶")
        step_forward_btn.clicked.connect(self._step_forward)
        controls_layout.addWidget(step_forward_btn)

        controls_layout.addStretch()

        # Speed control
        controls_layout.addWidget(QLabel("Speed:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "1x", "2x", "4x"])
        self.speed_combo.setCurrentText("1x")
        self.speed_combo.currentTextChanged.connect(self._on_speed_changed)
        controls_layout.addWidget(self.speed_combo)

        timeline_layout.addLayout(controls_layout)

        layout.addWidget(timeline_group)

    def _create_events_widget(self) -> QWidget:
        """Create the events list widget."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QHBoxLayout()
        events_label = QLabel("Events")
        events_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        header.addWidget(events_label)

        self.events_count_label = QLabel("(0)")
        self.events_count_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        header.addWidget(self.events_count_label)

        header.addStretch()

        # Add breakpoint button
        add_bp_btn = QPushButton("+ Breakpoint")
        add_bp_btn.clicked.connect(self._add_breakpoint)
        add_bp_btn.setMaximumWidth(100)
        header.addWidget(add_bp_btn)

        layout.addLayout(header)

        # Events list
        self.events_list = QListWidget()
        self.events_list.itemSelectionChanged.connect(self._on_event_selected)
        self.events_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #e5e7eb;
                border-radius: 4px;
                background-color: white;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 4px;
                border-left: 3px solid transparent;
            }
            QListWidget::item:selected {
                background-color: #dbeafe;
                border-left-color: #3b82f6;
            }
        """)
        layout.addWidget(self.events_list, 1)

        return widget

    def _create_details_widget(self) -> QWidget:
        """Create the event details widget."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        details_label = QLabel("Event Details")
        details_label.setStyleSheet("font-weight: bold; font-size: 12px; margin-bottom: 4px;")
        layout.addWidget(details_label)

        # Details text area
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setPlaceholderText("Select an event to view details")
        self.details_text.setStyleSheet("""
            QTextEdit {
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.details_text, 1)

        return widget

    def _setup_playback_timer(self) -> None:
        """Setup the playback timer."""
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self._advance_playback)
        self.playback_timer.setInterval(1000)  # Default 1 second per event

    def _load_session(self) -> None:
        """Load a session recording file."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Session Recording",
            "sessions",
            "JSON Files (*.json);;All Files (*)"
        )

        if not filename:
            return

        try:
            import json

            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle different session formats
            if isinstance(data, list):
                self.session_events = data
            elif isinstance(data, dict) and 'events' in data:
                self.session_events = data['events']
            else:
                raise ValueError("Unrecognized session format")

            self._populate_events()
            self.current_position = 0
            self._update_position()

            log.info(f"Loaded session with {len(self.session_events)} events from {filename}")
            QMessageBox.information(
                self,
                "Session Loaded",
                f"Loaded {len(self.session_events)} events from:\n{filename}"
            )

        except Exception as e:
            log.error(f"Failed to load session: {e}")
            QMessageBox.critical(self, "Load Error", f"Failed to load session: {e}")

    def _populate_events(self) -> None:
        """Populate the events list."""
        self.events_list.clear()

        for i, event in enumerate(self.session_events):
            # Format event summary
            event_type = event.get('type', 'unknown')
            timestamp = event.get('timestamp', '')
            summary = f"[{i:04d}] {timestamp[:19]} - {event_type}"

            item = QListWidgetItem(summary)
            item.setData(Qt.UserRole, i)

            # Mark breakpoints
            if i in self.breakpoints:
                item.setForeground(Qt.red)
                item.setText(f"● {summary}")

            self.events_list.addItem(item)

        # Update timeline
        self.timeline_slider.setMaximum(max(0, len(self.session_events) - 1))
        self.events_count_label.setText(f"({len(self.session_events)})")

    def _on_event_selected(self) -> None:
        """Handle event selection."""
        items = self.events_list.selectedItems()
        if items:
            index = items[0].data(Qt.UserRole)
            self._show_event_details(index)
            self.event_selected.emit(index)

    def _show_event_details(self, index: int) -> None:
        """Show details for an event."""
        if 0 <= index < len(self.session_events):
            event = self.session_events[index]

            # Format event details
            import json
            details = json.dumps(event, indent=2, default=str)
            self.details_text.setPlainText(details)

    def _on_slider_changed(self, value: int) -> None:
        """Handle timeline slider change."""
        self.current_position = value
        self._update_position()

        # Select corresponding event
        if 0 <= value < self.events_list.count():
            self.events_list.setCurrentRow(value)

    def _on_speed_changed(self, speed_text: str) -> None:
        """Handle speed change."""
        speed_value = float(speed_text.replace('x', ''))
        self.playback_speed = speed_value

        # Update timer interval
        base_interval = 1000  # 1 second
        new_interval = int(base_interval / speed_value)
        self.playback_timer.setInterval(new_interval)

        log.debug(f"Playback speed changed to {speed_value}x (interval: {new_interval}ms)")

    def _toggle_playback(self) -> None:
        """Toggle play/pause."""
        if self.is_playing:
            self._pause_playback()
        else:
            self._start_playback()

    def _start_playback(self) -> None:
        """Start playback."""
        if not self.session_events:
            QMessageBox.warning(self, "No Session", "Please load a session first")
            return

        self.is_playing = True
        self.play_pause_btn.setText("Pause")
        self.play_pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #f59e0b;
                color: white;
                border: none;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d97706;
            }
        """)
        self.playback_timer.start()
        self.playback_started.emit()
        log.info("Playback started")

    def _pause_playback(self) -> None:
        """Pause playback."""
        self.is_playing = False
        self.play_pause_btn.setText("Play")
        self.play_pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        self.playback_timer.stop()
        self.playback_paused.emit()
        log.info("Playback paused")

    def _stop_playback(self) -> None:
        """Stop playback and reset to beginning."""
        self.is_playing = False
        self.play_pause_btn.setText("Play")
        self.playback_timer.stop()
        self.current_position = 0
        self._update_position()
        self.playback_stopped.emit()
        log.info("Playback stopped")

    def _advance_playback(self) -> None:
        """Advance playback to next event."""
        if self.current_position < len(self.session_events) - 1:
            self.current_position += 1
            self._update_position()

            # Check for breakpoint
            if self.current_position in self.breakpoints:
                self._pause_playback()
                log.info(f"Hit breakpoint at event {self.current_position}")
        else:
            # End of session
            self._pause_playback()

    def _step_forward(self) -> None:
        """Step forward one event."""
        if self.current_position < len(self.session_events) - 1:
            self.current_position += 1
            self._update_position()

    def _step_backward(self) -> None:
        """Step backward one event."""
        if self.current_position > 0:
            self.current_position -= 1
            self._update_position()

    def _update_position(self) -> None:
        """Update the current position display."""
        total = len(self.session_events)
        current = self.current_position + 1 if total > 0 else 0

        self.position_label.setText(f"{current} / {total}")
        self.timeline_slider.setValue(self.current_position)

        # Update selection
        if 0 <= self.current_position < self.events_list.count():
            self.events_list.setCurrentRow(self.current_position)

        self.position_changed.emit(self.current_position, total)

    def _add_breakpoint(self) -> None:
        """Add a breakpoint at the current position."""
        if not self.session_events:
            QMessageBox.warning(self, "No Session", "Please load a session first")
            return

        if self.current_position not in self.breakpoints:
            self.breakpoints.append(self.current_position)
            self.breakpoints.sort()
            self._populate_events()  # Refresh to show breakpoint
            log.info(f"Added breakpoint at event {self.current_position}")
        else:
            # Remove breakpoint
            self.breakpoints.remove(self.current_position)
            self._populate_events()
            log.info(f"Removed breakpoint at event {self.current_position}")

    def load_session_data(self, events: List[Dict[str, Any]]) -> None:
        """Load session data programmatically."""
        self.session_events = events
        self._populate_events()
        self.current_position = 0
        self._update_position()
        log.info(f"Loaded session with {len(events)} events")

    def clear(self) -> None:
        """Clear the session replay viewer."""
        self.session_events.clear()
        self.breakpoints.clear()
        self.current_position = 0
        self.events_list.clear()
        self.details_text.clear()
        self._update_position()
        if self.is_playing:
            self._pause_playback()
