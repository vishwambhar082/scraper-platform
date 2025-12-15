"""
Engine factory for creating engines based on configuration.

This provides dependency injection and unified engine creation.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from src.common.logging_utils import get_logger
from src.engines.base_engine import BaseEngine, EngineConfig
from src.engines.groq_browser import GroqBrowserAutomationClient
from src.engines.http_engine import HttpEngine
from src.engines.rate_limiter import SimpleRateLimiter
from src.engines.selenium_engine import BrowserSession, open_with_session
from src.sessions.session_manager import SessionRecord

log = get_logger("engine-factory")


def create_engine(
    engine_type: str,
    source_config: Mapping[str, Any],
    *,
    proxy: Optional[str] = None,
    session_record: Optional[SessionRecord] = None,
) -> BaseEngine:
    """
    Create an engine instance based on type and configuration.

    Args:
        engine_type: Engine type ('http', 'selenium', 'playwright', 'groq_browser')
        source_config: Source configuration dict
        proxy: Optional proxy string
        session_record: Optional session record for browser engines

    Returns:
        BaseEngine instance

    Raises:
        ValueError if engine_type is unsupported
    """
    engine_cfg = source_config.get("engine", {})
    rate_limit_cfg = source_config.get("rate_limits", {})

    # Build rate limiter if configured
    rate_limiter: Optional[SimpleRateLimiter] = None
    if rate_limit_cfg.get("max_qps"):
        min_delay = 1.0 / rate_limit_cfg["max_qps"]
        rate_limiter = SimpleRateLimiter(min_delay=min_delay, max_delay=min_delay * 2)

    # Build engine config
    config = EngineConfig(
        proxy=proxy,
        timeout=float(engine_cfg.get("timeout", 30.0)),
        max_retries=int(engine_cfg.get("max_retries", 3)),
        retry_backoff=float(engine_cfg.get("retry_backoff", 1.0)),
        headers=engine_cfg.get("headers"),
        rate_limiter=rate_limiter,
    )

    engine_type = engine_type.lower().strip()

    if engine_type in ("http", "requests", "rest"):
        return HttpEngine(config)

    elif engine_type in ("selenium", "chrome", "webdriver"):
        # Selenium engine is special - it returns BrowserSession, not BaseEngine
        # We'll create a wrapper or use it directly
        if session_record:
            return SeleniumEngineWrapper(session_record, config)
        else:
            raise ValueError("Selenium engine requires session_record")

    elif engine_type in ("playwright", "pw"):
        # Playwright is async - needs special handling
        raise NotImplementedError("Playwright engine wrapper not yet implemented")

    elif engine_type in ("groq", "groq_browser", "groq-browser", "browserbase"):
        # Groq browser automation
        api_key = source_config.get("llm", {}).get("api_key") or None
        return GroqBrowserEngineWrapper(config, api_key=api_key)

    else:
        raise ValueError(f"Unsupported engine type: {engine_type}")


class SeleniumEngineWrapper(BaseEngine):
    """Wrapper to make Selenium BrowserSession work as BaseEngine."""

    def __init__(self, session_record: SessionRecord, config: EngineConfig):
        super().__init__(config)
        self.session_record = session_record
        self._browser_session: Optional[BrowserSession] = None

    def fetch(self, url: str, **kwargs: Any) -> Any:  # Returns EngineResult
        """Fetch using Selenium."""
        if not self._browser_session:
            self._browser_session = open_with_session(url, self.session_record)
        else:
            self._browser_session.navigate(url)

        driver = self._browser_session.driver
        from src.engines.base_engine import EngineResult

        return EngineResult(
            url=driver.current_url,
            status_code=200,  # Selenium doesn't expose status code easily
            content=driver.page_source,
            headers={},
            elapsed_seconds=0.0,
            metadata={"driver": "selenium"},
        )

    def cleanup(self) -> None:
        """Close browser session."""
        if self._browser_session:
            self._browser_session.quit()
            self._browser_session = None
        self._mark_closed()


class GroqBrowserEngineWrapper(BaseEngine):
    """Wrapper to make Groq browser automation work as BaseEngine."""

    def __init__(self, config: EngineConfig, api_key: Optional[str] = None):
        super().__init__(config)
        self._client = GroqBrowserAutomationClient(api_key=api_key)

    def fetch(self, url: str, **kwargs: Any) -> Any:  # Returns EngineResult
        """Fetch using Groq browser automation."""
        instructions = kwargs.get("instructions", f"Navigate to {url} and extract the page content")
        result = self._client.run_workflow(
            instructions,
            start_url=url,
            max_browser_time=int(self.config.timeout),
        )

        from src.engines.base_engine import EngineResult

        return EngineResult(
            url=url,
            status_code=200,
            content=result.content,
            headers={},
            elapsed_seconds=0.0,  # Groq doesn't expose timing easily
            metadata={
                "executed_tools": result.executed_tools,
                "usage": result.usage,
            },
        )

    def cleanup(self) -> None:
        """Cleanup Groq client."""
        # Groq client is stateless, nothing to clean up
        self._mark_closed()


__all__ = ["create_engine", "SeleniumEngineWrapper", "GroqBrowserEngineWrapper"]

