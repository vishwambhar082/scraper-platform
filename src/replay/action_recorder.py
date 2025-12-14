"""
Action recorder for deterministic session replay.
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RecordedAction:
    """Single recorded action."""
    timestamp: float  # Seconds since session start
    action_type: str  # 'click', 'input', 'navigate', 'screenshot', 'network'
    target: Optional[str] = None  # Element selector or URL
    value: Optional[Any] = None  # Input value, response data, etc.
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RecordedAction':
        """Create from dictionary."""
        return cls(**data)


class ActionRecorder:
    """
    Records user and system actions for deterministic replay.

    Captures:
    - Click events (element, coordinates)
    - Input events (element, value)
    - Navigation (URL)
    - Screenshots (base64 or file path)
    - Network requests/responses
    """

    def __init__(self, session_id: str, output_dir: Path):
        """
        Initialize action recorder.

        Args:
            session_id: Unique session identifier
            output_dir: Directory to save recordings
        """
        self.session_id = session_id
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.start_time = datetime.utcnow()
        self.actions: List[RecordedAction] = []
        self.screenshots: List[Dict[str, Any]] = []
        self.network_log: List[Dict[str, Any]] = []

    def record_click(
        self,
        element_selector: str,
        x: int,
        y: int,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record click action.

        Args:
            element_selector: CSS selector or XPath
            x: X coordinate
            y: Y coordinate
            metadata: Additional metadata
        """
        action = RecordedAction(
            timestamp=self._get_timestamp(),
            action_type='click',
            target=element_selector,
            value={'x': x, 'y': y},
            metadata=metadata
        )
        self.actions.append(action)
        logger.debug(f"Recorded click: {element_selector} at ({x}, {y})")

    def record_input(
        self,
        element_selector: str,
        value: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record input action.

        Args:
            element_selector: CSS selector or XPath
            value: Input value
            metadata: Additional metadata
        """
        action = RecordedAction(
            timestamp=self._get_timestamp(),
            action_type='input',
            target=element_selector,
            value=value,
            metadata=metadata
        )
        self.actions.append(action)
        logger.debug(f"Recorded input: {element_selector} = {value}")

    def record_navigation(
        self,
        url: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record navigation action.

        Args:
            url: Target URL
            metadata: Additional metadata
        """
        action = RecordedAction(
            timestamp=self._get_timestamp(),
            action_type='navigate',
            target=url,
            metadata=metadata
        )
        self.actions.append(action)
        logger.debug(f"Recorded navigation: {url}")

    def record_screenshot(
        self,
        screenshot_data: bytes,
        step_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Record screenshot.

        Args:
            screenshot_data: PNG screenshot data
            step_name: Step identifier
            metadata: Additional metadata

        Returns:
            Path to saved screenshot
        """
        timestamp = self._get_timestamp()
        filename = f"screenshot_{len(self.screenshots):04d}_{step_name}.png"
        filepath = self.output_dir / filename

        # Save screenshot
        filepath.write_bytes(screenshot_data)

        # Record metadata
        self.screenshots.append({
            'timestamp': timestamp,
            'step': step_name,
            'filename': filename,
            'size': len(screenshot_data),
            'metadata': metadata
        })

        action = RecordedAction(
            timestamp=timestamp,
            action_type='screenshot',
            target=filename,
            metadata=metadata
        )
        self.actions.append(action)

        logger.debug(f"Recorded screenshot: {filename}")
        return filepath

    def record_network(
        self,
        request: Dict[str, Any],
        response: Dict[str, Any],
        duration_ms: Optional[float] = None
    ):
        """
        Record network request/response.

        Args:
            request: Request details (method, url, headers, body)
            response: Response details (status, headers, body)
            duration_ms: Request duration in milliseconds
        """
        timestamp = self._get_timestamp()

        network_entry = {
            'timestamp': timestamp,
            'request': request,
            'response': response,
            'duration_ms': duration_ms
        }
        self.network_log.append(network_entry)

        action = RecordedAction(
            timestamp=timestamp,
            action_type='network',
            target=request.get('url'),
            value={
                'method': request.get('method'),
                'status': response.get('status')
            },
            metadata={'duration_ms': duration_ms}
        )
        self.actions.append(action)

        logger.debug(f"Recorded network: {request.get('method')} {request.get('url')}")

    def save_session(self) -> Path:
        """
        Save recorded session to disk.

        Returns:
            Path to session file
        """
        session_file = self.output_dir / f"{self.session_id}.replay.json"

        session_data = {
            'metadata': {
                'session_id': self.session_id,
                'start_time': self.start_time.isoformat(),
                'end_time': datetime.utcnow().isoformat(),
                'duration_seconds': (datetime.utcnow() - self.start_time).total_seconds(),
                'action_count': len(self.actions),
                'screenshot_count': len(self.screenshots),
                'network_count': len(self.network_log)
            },
            'actions': [action.to_dict() for action in self.actions],
            'screenshots': self.screenshots,
            'network_log': self.network_log
        }

        session_file.write_text(json.dumps(session_data, indent=2))
        logger.info(f"Session saved: {session_file}")

        return session_file

    def _get_timestamp(self) -> float:
        """Get timestamp in seconds since session start."""
        return (datetime.utcnow() - self.start_time).total_seconds()


class SeleniumRecorder(ActionRecorder):
    """
    ActionRecorder with Selenium integration.

    Automatically captures actions from Selenium WebDriver.
    """

    def wrap_driver(self, driver):
        """
        Wrap Selenium driver to auto-record actions.

        Args:
            driver: Selenium WebDriver instance

        Returns:
            Wrapped driver that records all actions
        """
        original_get = driver.get
        original_find_element = driver.find_element

        def recorded_get(url):
            self.record_navigation(url)
            return original_get(url)

        def recorded_find_element(*args, **kwargs):
            element = original_find_element(*args, **kwargs)

            # Wrap element methods
            original_click = element.click
            original_send_keys = element.send_keys

            def recorded_click():
                # Get element info
                selector = self._get_element_selector(element)
                location = element.location
                self.record_click(selector, location['x'], location['y'])
                return original_click()

            def recorded_send_keys(value):
                selector = self._get_element_selector(element)
                self.record_input(selector, value)
                return original_send_keys(value)

            element.click = recorded_click
            element.send_keys = recorded_send_keys

            return element

        driver.get = recorded_get
        driver.find_element = recorded_find_element

        return driver

    def _get_element_selector(self, element) -> str:
        """Get CSS selector or XPath for element."""
        try:
            # Try to get ID
            element_id = element.get_attribute('id')
            if element_id:
                return f"#{element_id}"

            # Try to get class
            element_class = element.get_attribute('class')
            if element_class:
                return f".{element_class.split()[0]}"

            # Fallback to tag name
            return element.tag_name

        except:
            return "unknown"


class PlaywrightRecorder(ActionRecorder):
    """
    ActionRecorder with Playwright integration.

    Automatically captures actions from Playwright.
    """

    async def attach_to_page(self, page):
        """
        Attach recorder to Playwright page.

        Args:
            page: Playwright Page instance
        """
        # Record navigations
        page.on('framenavigated', lambda frame:
            self.record_navigation(frame.url) if frame == page.main_frame else None
        )

        # Record network
        page.on('request', self._on_request)
        page.on('response', self._on_response)

        # Record console logs
        page.on('console', lambda msg:
            logger.debug(f"Console: {msg.text}")
        )

        self._request_map = {}

    def _on_request(self, request):
        """Handle request event."""
        self._request_map[request.url] = {
            'method': request.method,
            'url': request.url,
            'headers': request.headers,
            'timestamp': datetime.utcnow()
        }

    def _on_response(self, response):
        """Handle response event."""
        request_data = self._request_map.get(response.url, {})
        duration = None

        if request_data.get('timestamp'):
            duration = (datetime.utcnow() - request_data['timestamp']).total_seconds() * 1000

        self.record_network(
            request=request_data,
            response={
                'status': response.status,
                'url': response.url,
                'headers': response.headers
            },
            duration_ms=duration
        )
