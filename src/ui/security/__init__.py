"""
Security module for desktop application.
"""

from .lock_screen import LockScreen, SetupPinDialog, AuthManager, IdleMonitor
from .audit_viewer import AuditViewer, EventDetailsDialog, SecuritySettings

__all__ = [
    'LockScreen',
    'SetupPinDialog',
    'AuthManager',
    'IdleMonitor',
    'AuditViewer',
    'EventDetailsDialog',
    'SecuritySettings',
]
