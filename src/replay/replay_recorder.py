"""
Formalized replay recorder for deterministic playback.

Records all actions, network calls, and DOM snapshots.
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    """Types of recordable actions."""
    CLICK = "click"
    INPUT = "input"
    NAVIGATION = "navigation"
    SCROLL = "scroll"
    SCREENSHOT = "screenshot"
    WAIT = "wait"
    NETWORK_REQUEST = "network_request"
    NETWORK_RESPONSE = "network_response"
    DOM_SNAPSHOT = "dom_snapshot"
    CUSTOM = "custom"


@dataclass
class RecordedAction:
    """Single recorded action."""
    action_type: ActionType
    timestamp: float  # Seconds since session start
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReplaySession:
    """Complete replay session."""
    session_id: str
    started_at: datetime
    finished_at: Optional[datetime]
    pipeline_id: str
    source: str
    actions: List[RecordedAction] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReplayRecorder:
    """
    Records actions for deterministic replay.

    Thread-safe recorder with automatic timestamping.
    """

    def __init__(self, session_id: str, pipeline_id: str, source: str):
        """
        Initialize recorder.

        Args:
            session_id: Unique session identifier
            pipeline_id: Pipeline being executed
            source: Data source
        """
        self.session = ReplaySession(
            session_id=session_id,
            started_at=datetime.utcnow(),
            finished_at=None,
            pipeline_id=pipeline_id,
            source=source
        )
        self.start_time = datetime.utcnow().timestamp()

    def _get_timestamp(self) -> float:
        """Get timestamp relative to session start."""
        return datetime.utcnow().timestamp() - self.start_time

    def record_click(
        self,
        selector: str,
        x: int,
        y: int,
        button: str = "left",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record click action.

        Args:
            selector: Element selector
            x: X coordinate
            y: Y coordinate
            button: Mouse button
            metadata: Optional metadata
        """
        action = RecordedAction(
            action_type=ActionType.CLICK,
            timestamp=self._get_timestamp(),
            data={
                'selector': selector,
                'x': x,
                'y': y,
                'button': button
            },
            metadata=metadata or {}
        )
        self.session.actions.append(action)
        logger.debug(f"Recorded click: {selector}")

    def record_input(
        self,
        selector: str,
        value: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record input action.

        Args:
            selector: Element selector
            value: Input value
            metadata: Optional metadata
        """
        action = RecordedAction(
            action_type=ActionType.INPUT,
            timestamp=self._get_timestamp(),
            data={
                'selector': selector,
                'value': value
            },
            metadata=metadata or {}
        )
        self.session.actions.append(action)
        logger.debug(f"Recorded input: {selector}")

    def record_navigation(
        self,
        url: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record navigation.

        Args:
            url: Target URL
            metadata: Optional metadata
        """
        action = RecordedAction(
            action_type=ActionType.NAVIGATION,
            timestamp=self._get_timestamp(),
            data={'url': url},
            metadata=metadata or {}
        )
        self.session.actions.append(action)
        logger.debug(f"Recorded navigation: {url}")

    def record_scroll(
        self,
        x: int,
        y: int,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record scroll action.

        Args:
            x: Horizontal scroll position
            y: Vertical scroll position
            metadata: Optional metadata
        """
        action = RecordedAction(
            action_type=ActionType.SCROLL,
            timestamp=self._get_timestamp(),
            data={'x': x, 'y': y},
            metadata=metadata or {}
        )
        self.session.actions.append(action)

    def record_screenshot(
        self,
        screenshot_path: str,
        step_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record screenshot.

        Args:
            screenshot_path: Path to screenshot file
            step_name: Step name
            metadata: Optional metadata
        """
        action = RecordedAction(
            action_type=ActionType.SCREENSHOT,
            timestamp=self._get_timestamp(),
            data={
                'path': screenshot_path,
                'step_name': step_name
            },
            metadata=metadata or {}
        )
        self.session.actions.append(action)
        logger.debug(f"Recorded screenshot: {step_name}")

    def record_wait(
        self,
        duration_ms: int,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record wait action.

        Args:
            duration_ms: Wait duration in milliseconds
            reason: Wait reason
            metadata: Optional metadata
        """
        action = RecordedAction(
            action_type=ActionType.WAIT,
            timestamp=self._get_timestamp(),
            data={
                'duration_ms': duration_ms,
                'reason': reason
            },
            metadata=metadata or {}
        )
        self.session.actions.append(action)

    def record_network_request(
        self,
        url: str,
        method: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record network request.

        Args:
            url: Request URL
            method: HTTP method
            headers: Request headers
            body: Request body
            metadata: Optional metadata
        """
        action = RecordedAction(
            action_type=ActionType.NETWORK_REQUEST,
            timestamp=self._get_timestamp(),
            data={
                'url': url,
                'method': method,
                'headers': headers or {},
                'body': body
            },
            metadata=metadata or {}
        )
        self.session.actions.append(action)

    def record_network_response(
        self,
        url: str,
        status_code: int,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        duration_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record network response.

        Args:
            url: Request URL
            status_code: HTTP status code
            headers: Response headers
            body: Response body (truncated if large)
            duration_ms: Request duration
            metadata: Optional metadata
        """
        # Truncate large bodies
        if body and len(body) > 10000:
            body = body[:10000] + "... [truncated]"

        action = RecordedAction(
            action_type=ActionType.NETWORK_RESPONSE,
            timestamp=self._get_timestamp(),
            data={
                'url': url,
                'status_code': status_code,
                'headers': headers or {},
                'body': body,
                'duration_ms': duration_ms
            },
            metadata=metadata or {}
        )
        self.session.actions.append(action)

    def record_dom_snapshot(
        self,
        html: str,
        step_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record DOM snapshot.

        Args:
            html: HTML content
            step_name: Step name
            metadata: Optional metadata
        """
        # Truncate large HTML
        if len(html) > 50000:
            html = html[:50000] + "... [truncated]"

        action = RecordedAction(
            action_type=ActionType.DOM_SNAPSHOT,
            timestamp=self._get_timestamp(),
            data={
                'html': html,
                'step_name': step_name
            },
            metadata=metadata or {}
        )
        self.session.actions.append(action)

    def record_custom(
        self,
        action_name: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record custom action.

        Args:
            action_name: Custom action name
            data: Action data
            metadata: Optional metadata
        """
        action = RecordedAction(
            action_type=ActionType.CUSTOM,
            timestamp=self._get_timestamp(),
            data={
                'action_name': action_name,
                **data
            },
            metadata=metadata or {}
        )
        self.session.actions.append(action)

    def finish(self):
        """Mark session as finished."""
        self.session.finished_at = datetime.utcnow()
        logger.info(f"Replay session finished: {self.session.session_id} ({len(self.session.actions)} actions)")

    def save(self, output_dir: Path) -> Path:
        """
        Save session to file.

        Args:
            output_dir: Output directory

        Returns:
            Path to saved file
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{self.session.session_id}.replay.json"
        filepath = output_dir / filename

        session_dict = {
            'session_id': self.session.session_id,
            'started_at': self.session.started_at.isoformat(),
            'finished_at': self.session.finished_at.isoformat() if self.session.finished_at else None,
            'pipeline_id': self.session.pipeline_id,
            'source': self.session.source,
            'metadata': self.session.metadata,
            'actions': [
                {
                    'action_type': a.action_type.value,
                    'timestamp': a.timestamp,
                    'data': a.data,
                    'metadata': a.metadata
                }
                for a in self.session.actions
            ]
        }

        filepath.write_text(json.dumps(session_dict, indent=2))
        logger.info(f"Replay session saved: {filepath}")

        return filepath

    @classmethod
    def load(cls, filepath: Path) -> ReplaySession:
        """
        Load session from file.

        Args:
            filepath: Path to replay file

        Returns:
            Loaded ReplaySession
        """
        data = json.loads(filepath.read_text())

        session = ReplaySession(
            session_id=data['session_id'],
            started_at=datetime.fromisoformat(data['started_at']),
            finished_at=datetime.fromisoformat(data['finished_at']) if data['finished_at'] else None,
            pipeline_id=data['pipeline_id'],
            source=data['source'],
            metadata=data['metadata'],
            actions=[
                RecordedAction(
                    action_type=ActionType(a['action_type']),
                    timestamp=a['timestamp'],
                    data=a['data'],
                    metadata=a['metadata']
                )
                for a in data['actions']
            ]
        )

        logger.info(f"Replay session loaded: {filepath}")
        return session
