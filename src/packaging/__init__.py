"""
Packaging and distribution utilities for the scraper platform.

This module provides:
- PyInstaller/Nuitka build configurations
- Auto-update mechanisms
- Installer generation
- Version management
"""

from .version import VERSION, get_version_info
from .updater import AutoUpdater, UpdateChecker
from .installer import InstallerBuilder

__all__ = [
    'VERSION',
    'get_version_info',
    'AutoUpdater',
    'UpdateChecker',
    'InstallerBuilder',
]
