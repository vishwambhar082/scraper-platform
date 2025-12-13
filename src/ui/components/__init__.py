"""
UI Components for the Scraper Platform Desktop Application.

This package contains modular, reusable components extracted from the main window
to improve maintainability and testability.
"""

from .dashboard import JobDashboard
from .pipeline_viewer import PipelineViewer
from .log_viewer import LogViewer
from .settings_editor import SettingsEditor
from .resource_monitor import ResourceMonitor
from .screenshot_gallery import ScreenshotGallery
from .replay_viewer import ReplayViewer

__all__ = [
    "JobDashboard",
    "PipelineViewer",
    "LogViewer",
    "SettingsEditor",
    "ResourceMonitor",
    "ScreenshotGallery",
    "ReplayViewer",
]
