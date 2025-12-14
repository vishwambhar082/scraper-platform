"""
Replay player for deterministic session playback.
"""

import json
import time
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List

from .action_recorder import RecordedAction

logger = logging.getLogger(__name__)


class ReplayPlayer:
    """
    Plays back recorded sessions deterministically.

    Can step through actions, set breakpoints, and compare with expected outcomes.
    """

    def __init__(self, session_file: Path):
        """
        Initialize replay player.

        Args:
            session_file: Path to recorded session file
        """
        self.session_file = session_file
        self.session_data = None
        self.actions: List[RecordedAction] = []
        self.current_index = 0
        self.is_playing = False
        self.is_paused = False
        self.playback_speed = 1.0
        self.breakpoints: set = set()
        self.event_callbacks: List[Callable] = []

        self._load_session()

    def _load_session(self):
        """Load session from file."""
        try:
            data = json.loads(self.session_file.read_text())
            self.session_data = data
            self.actions = [
                RecordedAction.from_dict(action)
                for action in data.get('actions', [])
            ]
            logger.info(f"Loaded session: {len(self.actions)} actions")
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            self.session_data = {}
            self.actions = []

    def play(self, speed: float = 1.0, start_from: int = 0):
        """
        Play session from beginning or specific index.

        Args:
            speed: Playback speed multiplier (1.0 = real-time)
            start_from: Index to start from
        """
        self.playback_speed = speed
        self.current_index = start_from
        self.is_playing = True
        self.is_paused = False

        logger.info(f"Starting playback from index {start_from}")

        last_timestamp = 0 if start_from == 0 else self.actions[start_from].timestamp

        while self.is_playing and self.current_index < len(self.actions):
            # Check if paused
            while self.is_paused:
                time.sleep(0.1)

            action = self.actions[self.current_index]

            # Check breakpoint
            if self.current_index in self.breakpoints:
                logger.info(f"Breakpoint at index {self.current_index}")
                self.pause()
                self._emit_event('breakpoint', {'index': self.current_index})
                continue

            # Wait for appropriate time (respecting playback speed)
            if self.current_index > 0:
                wait_time = (action.timestamp - last_timestamp) / self.playback_speed
                if wait_time > 0:
                    time.sleep(wait_time)

            # Execute action
            self._execute_action(action)

            # Emit progress event
            self._emit_event('action_executed', {
                'index': self.current_index,
                'action': action.to_dict(),
                'progress': (self.current_index + 1) / len(self.actions)
            })

            last_timestamp = action.timestamp
            self.current_index += 1

        self.is_playing = False
        logger.info("Playback completed")
        self._emit_event('playback_completed', {'final_index': self.current_index})

    def pause(self):
        """Pause playback."""
        self.is_paused = True
        logger.info("Playback paused")
        self._emit_event('playback_paused', {'index': self.current_index})

    def resume(self):
        """Resume playback."""
        self.is_paused = False
        logger.info("Playback resumed")
        self._emit_event('playback_resumed', {'index': self.current_index})

    def stop(self):
        """Stop playback."""
        self.is_playing = False
        self.is_paused = False
        logger.info("Playback stopped")
        self._emit_event('playback_stopped', {'index': self.current_index})

    def step_forward(self) -> bool:
        """
        Execute next action (step mode).

        Returns:
            True if action executed, False if at end
        """
        if self.current_index >= len(self.actions):
            return False

        action = self.actions[self.current_index]
        self._execute_action(action)

        self._emit_event('action_executed', {
            'index': self.current_index,
            'action': action.to_dict()
        })

        self.current_index += 1
        return True

    def step_backward(self) -> bool:
        """
        Step backward (note: may not be fully reversible).

        Returns:
            True if stepped back, False if at beginning
        """
        if self.current_index <= 0:
            return False

        self.current_index -= 1
        logger.info(f"Stepped back to index {self.current_index}")
        return True

    def seek(self, index: int):
        """Seek to specific action index."""
        if 0 <= index < len(self.actions):
            self.current_index = index
            logger.info(f"Seeked to index {index}")
            self._emit_event('seeked', {'index': index})

    def set_breakpoint(self, index: int):
        """Set breakpoint at action index."""
        self.breakpoints.add(index)
        logger.info(f"Breakpoint set at index {index}")

    def clear_breakpoint(self, index: int):
        """Clear breakpoint at action index."""
        self.breakpoints.discard(index)

    def subscribe(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Subscribe to playback events."""
        self.event_callbacks.append(callback)

    def _execute_action(self, action: RecordedAction):
        """
        Execute a single recorded action.

        Note: This is a simulation. In real implementation, this would
        interact with actual browser/scraper.
        """
        logger.info(f"Executing action: {action.action_type} - {action.target}")

        # TODO: Implement actual action execution
        # This would interact with Selenium/Playwright to replay the action

        if action.action_type == 'click':
            # driver.find_element(By.CSS_SELECTOR, action.target).click()
            pass

        elif action.action_type == 'input':
            # driver.find_element(By.CSS_SELECTOR, action.target).send_keys(action.value)
            pass

        elif action.action_type == 'navigate':
            # driver.get(action.target)
            pass

        # For now, just log
        logger.debug(f"Action simulated: {action.action_type}")

    def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit event to subscribers."""
        for callback in self.event_callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Event callback error: {e}")

    def get_metadata(self) -> Dict[str, Any]:
        """Get session metadata."""
        return self.session_data.get('metadata', {})

    def get_action(self, index: int) -> Optional[RecordedAction]:
        """Get action at specific index."""
        if 0 <= index < len(self.actions):
            return self.actions[index]
        return None

    def get_current_action(self) -> Optional[RecordedAction]:
        """Get current action."""
        return self.get_action(self.current_index)

    def get_screenshots(self) -> List[Dict[str, Any]]:
        """Get all screenshot metadata."""
        return self.session_data.get('screenshots', [])

    def get_network_log(self) -> List[Dict[str, Any]]:
        """Get network request/response log."""
        return self.session_data.get('network_log', [])
