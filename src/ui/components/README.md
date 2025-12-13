# UI Components

This directory contains modular, reusable UI components extracted from the main window to improve maintainability and testability.

## Architecture

All components follow these design principles:

- **Single Responsibility**: Each component handles one specific aspect of the UI
- **Signal/Slot Communication**: Components use Qt signals for loose coupling
- **Independent Testing**: Each component can be tested in isolation
- **Consistent API**: All components follow similar initialization and update patterns

## Components

### 1. JobDashboard (`dashboard.py`)

**Purpose**: Comprehensive job management interface

**Features**:
- Job list table with real-time updates
- Start/stop job controls
- Job selection and filtering
- Status indicators with color coding
- Automatic refresh every 2 seconds

**Signals**:
- `job_started(str)` - Emitted when a job is started (job_id)
- `job_stopped(str)` - Emitted when a job is stopped (job_id)
- `job_selected(str)` - Emitted when a job is selected (job_id)

**Usage**:
```python
from src.ui.components import JobDashboard

dashboard = JobDashboard()
dashboard.job_selected.connect(lambda job_id: print(f"Selected: {job_id}"))
dashboard.refresh()
```

---

### 2. PipelineViewer (`pipeline_viewer.py`)

**Purpose**: Real-time pipeline execution visualization

**Features**:
- Step-by-step progress tracking
- DAG visualization with zoom controls
- Step timing and status display
- Detailed step information
- Tree view of pipeline steps

**Signals**:
- `step_selected(str)` - Emitted when a step is selected (step_name)

**Usage**:
```python
from src.ui.components import PipelineViewer

viewer = PipelineViewer()
viewer.load_run("run_id_12345")
viewer.step_selected.connect(lambda step: print(f"Step: {step}"))
```

**Methods**:
- `load_run(run_id: str)` - Load a pipeline run for visualization
- `refresh()` - Refresh the pipeline view
- `update_step_status(step_id: str, status: str)` - Update step status in real-time
- `clear()` - Clear the viewer

---

### 3. LogViewer (`log_viewer.py`)

**Purpose**: Comprehensive log display with filtering

**Features**:
- Live log streaming with auto-scroll
- Multi-level filtering (search, level, module)
- Export to text or JSON
- Persistent log storage
- Color-coded display (terminal style)
- Buffer management (10,000 entries max)

**Signals**:
- `logs_exported(str)` - Emitted when logs are exported (filename)

**Usage**:
```python
from src.ui.components import LogViewer

log_viewer = LogViewer()
log_viewer.append_log("INFO", "Application started", module="ui.main")
log_viewer.set_log_level_filter("ERROR")
log_viewer.export_logs()
```

**Methods**:
- `append_log(level: str, message: str, module: str = "")` - Add a log entry
- `clear()` - Clear all logs (with confirmation)
- `export_logs()` - Export logs to file (TXT or JSON)
- `set_log_level_filter(level: str)` - Set log level filter programmatically
- `get_log_count()` - Get total number of log entries

---

### 4. SettingsEditor (`settings_editor.py`)

**Purpose**: Environment variable and configuration management

**Features**:
- Environment variables table (editable)
- Add/remove variables
- Save to .env file with backup
- Load from .env file
- Input validation
- Real-time change detection

**Signals**:
- `settings_changed()` - Emitted when any setting is modified
- `settings_saved(str)` - Emitted when settings are saved (filepath)

**Usage**:
```python
from src.ui.components import SettingsEditor

settings = SettingsEditor()
settings.settings_changed.connect(lambda: print("Settings changed"))
settings.set_variable("DB_URL", "postgresql://localhost/db")
print(settings.get_variable("DB_URL"))
```

**Methods**:
- `get_variable(key: str)` - Get an environment variable value
- `set_variable(key: str, value: str)` - Set an environment variable
- `get_all_variables()` - Get all environment variables as dict

---

### 5. ResourceMonitor (`resource_monitor.py`)

**Purpose**: Real-time system resource monitoring

**Features**:
- CPU usage chart (60 data points)
- Memory usage chart
- Disk usage chart
- Network statistics
- Summary cards
- Auto-refresh (configurable interval)
- Graceful fallback when psutil not available

**Signals**:
- `resource_updated(dict)` - Emitted when resources are updated

**Usage**:
```python
from src.ui.components import ResourceMonitor

monitor = ResourceMonitor()
monitor.resource_updated.connect(lambda data: print(f"CPU: {data['cpu']}%"))
monitor.set_update_interval(500)  # Update every 500ms
monitor.start_monitoring()
```

**Methods**:
- `refresh()` - Manually refresh resource data
- `set_update_interval(interval_ms: int)` - Set update interval
- `start_monitoring()` - Start automatic updates
- `stop_monitoring()` - Stop automatic updates

**Dependencies**:
- `psutil` (optional) - Install with `pip install psutil` for real data
- Falls back to simulated data if psutil not available

---

### 6. ScreenshotGallery (`screenshot_gallery.py`)

**Purpose**: Screenshot browsing and management

**Features**:
- Thumbnail grid view with icons
- Fullscreen preview
- Timeline navigation with slider
- Screenshot metadata display
- Export selected screenshots
- Browse custom folders
- Support for PNG, JPG, GIF, BMP

**Signals**:
- `screenshot_selected(str)` - Emitted when a screenshot is selected (filepath)
- `screenshot_opened(str)` - Emitted when opening screenshot fullscreen (filepath)

**Usage**:
```python
from src.ui.components import ScreenshotGallery
from pathlib import Path

gallery = ScreenshotGallery()
gallery.set_screenshot_dir(Path("screenshots"))
gallery.screenshot_selected.connect(lambda path: print(f"Selected: {path}"))
gallery.refresh()
```

**Methods**:
- `refresh()` - Reload screenshots from directory
- `set_screenshot_dir(directory: Path)` - Set the screenshot directory
- `get_selected_screenshot()` - Get currently selected screenshot path

---

### 7. ReplayViewer (`replay_viewer.py`)

**Purpose**: Session replay and debugging

**Features**:
- Play/pause/stop controls
- Step forward/backward navigation
- Variable speed playback (0.25x to 4x)
- Breakpoint management
- Event inspection (JSON details)
- Timeline scrubbing
- Session file loading (JSON format)

**Signals**:
- `playback_started()` - Emitted when playback starts
- `playback_paused()` - Emitted when playback pauses
- `playback_stopped()` - Emitted when playback stops
- `position_changed(int, int)` - Emitted when position changes (position, total)
- `event_selected(int)` - Emitted when an event is selected (event_index)

**Usage**:
```python
from src.ui.components import ReplayViewer

replay = ReplayViewer()
replay.load_session_data([
    {"type": "click", "timestamp": "2025-01-01T12:00:00", "element": "button"},
    {"type": "navigate", "timestamp": "2025-01-01T12:00:01", "url": "https://example.com"}
])
replay.playback_started.connect(lambda: print("Playback started"))
```

**Methods**:
- `load_session_data(events: List[Dict[str, Any]])` - Load session programmatically
- `clear()` - Clear the replay viewer

**Session Format**:
```json
[
  {
    "type": "event_type",
    "timestamp": "2025-01-01T12:00:00",
    "data": { /* event-specific data */ }
  }
]
```

---

## Integration with MainWindow

To integrate these components into the main window:

```python
from src.ui.components import (
    JobDashboard,
    PipelineViewer,
    LogViewer,
    SettingsEditor,
    ResourceMonitor,
    ScreenshotGallery,
    ReplayViewer,
)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Create components
        self.dashboard = JobDashboard()
        self.pipeline_viewer = PipelineViewer()
        self.log_viewer = LogViewer()
        self.settings = SettingsEditor()
        self.resources = ResourceMonitor()
        self.gallery = ScreenshotGallery()
        self.replay = ReplayViewer()

        # Connect signals
        self.dashboard.job_selected.connect(self.on_job_selected)
        self.log_viewer.logs_exported.connect(self.on_logs_exported)

        # Add to layout
        # ... add components to tabs or splitters ...

    def on_job_selected(self, job_id: str):
        # Load pipeline viewer with this job
        self.pipeline_viewer.load_run(job_id)

        # Get job info from dashboard
        job_info = self.dashboard.get_job_info(job_id)
        if job_info:
            print(f"Selected job: {job_info}")
```

## Component Communication

Components communicate via Qt signals to maintain loose coupling:

```
┌─────────────────┐
│  JobDashboard   │──job_selected──┐
└─────────────────┘                │
                                   ▼
                          ┌──────────────────┐
                          │  MainWindow      │
                          │  (Coordinator)   │
                          └──────────────────┘
                                   │
                                   ▼
┌─────────────────┐         ┌──────────────┐
│ PipelineViewer  │◄────────│  load_run()  │
└─────────────────┘         └──────────────┘
```

## Testing

Each component can be tested independently:

```python
# test_dashboard.py
import pytest
from PySide6.QtWidgets import QApplication
from src.ui.components import JobDashboard

@pytest.fixture
def app():
    return QApplication([])

def test_dashboard_creation(app):
    dashboard = JobDashboard()
    assert dashboard is not None
    assert dashboard.jobs_table.rowCount() == 0

def test_job_started_signal(app, qtbot):
    dashboard = JobDashboard()

    with qtbot.waitSignal(dashboard.job_started, timeout=1000) as blocker:
        # Simulate job start
        dashboard._start_job()

    assert blocker.signal_triggered
```

## Styling

All components use consistent styling:

- **Color Palette**:
  - Primary: `#3b82f6` (blue)
  - Success: `#10b981` (green)
  - Warning: `#f59e0b` (amber)
  - Danger: `#ef4444` (red)
  - Gray: `#6b7280` (neutral)

- **Borders**: `#e5e7eb` (light gray)
- **Background**: `#f9fafb` (off-white)
- **Text**: `#1f2937` (dark gray)

## File Statistics

```
Total Components: 7
Total Lines: ~3,500 (extracted from 3,171-line main_window.py)
Average Component Size: ~500 lines
Total Size: ~100KB
```

## Benefits of Modular Architecture

1. **Maintainability**: Each component is focused and easy to understand
2. **Testability**: Components can be unit tested in isolation
3. **Reusability**: Components can be used in different contexts
4. **Performance**: Components load only when needed
5. **Team Development**: Multiple developers can work on different components
6. **Documentation**: Each component has clear purpose and API

## Future Enhancements

Potential additions:

- **JobEditor**: Create/edit job configurations
- **NotificationCenter**: Centralized notifications and alerts
- **ChartLibrary**: Reusable chart components
- **DataExplorer**: Browse and query scraped data
- **ThemeSelector**: Visual theme customization

## Dependencies

All components depend on:
- `PySide6` (Qt for Python)
- `src.common.logging_utils`

Optional dependencies:
- `psutil` - For ResourceMonitor (real system metrics)
- `src.scheduler.scheduler_db_adapter` - For PipelineViewer (run tracking)
- `src.ui.job_manager` - For JobDashboard (job management)
- `src.ui.workflow_graph` - For PipelineViewer (DAG visualization)

## License

See project root LICENSE file.
