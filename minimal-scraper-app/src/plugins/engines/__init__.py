"""Engine plugins wrap HTTP/browser helpers for reuse across scrapers."""

from src.engines.playwright_engine import goto_with_retry
from src.engines.selenium_engine import open_with_session

__all__ = ["goto_with_retry", "open_with_session"]
