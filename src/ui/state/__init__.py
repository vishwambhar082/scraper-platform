"""
Event-driven state management for the UI control plane.

Implements a Redux-like pattern with:
- Centralized application state
- Action-based state mutations
- Event subscriptions
- State persistence
"""

from .store import AppStore, AppState
from .actions import Action, ActionType
from .events import EventBus, Event, EventType
from .middleware import StateMiddleware, LoggingMiddleware, PersistenceMiddleware

__all__ = [
    'AppStore',
    'AppState',
    'Action',
    'ActionType',
    'EventBus',
    'Event',
    'EventType',
    'StateMiddleware',
    'LoggingMiddleware',
    'PersistenceMiddleware',
]
