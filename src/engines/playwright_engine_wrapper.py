"""
Complete Playwright Engine Wrapper

Implements BaseEngine interface with full Playwright browser automation support.
Provides async browser control, auto-waiting, screenshot capture, and HAR recording.

Author: Scraper Platform Team
Date: 2025-12-13
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional
from pathlib import Path

from src.common.logging_utils import get_logger, safe_log, sanitize_for_log
from .base_engine import BaseEngine, EngineConfig, EngineResult, EngineError, RateLimitError

log = get_logger("playwright-engine")


class PlaywrightEngine(BaseEngine):
    """
    Playwright-based browser automation engine.

    Features:
    - Async browser automation
    - Auto-waiting for elements
    - Screenshot capture
    - HAR (HTTP Archive) recording
    - Network request interception
    - Cookie management
    - Headed/headless mode
    - Multi-browser support (Chromium, Firefox, WebKit)
    - Anti-detection features
    """

    def __init__(
        self,
        config: EngineConfig,
        *,
        browser_type: str = "chromium",
        headless: bool = True,
        user_agent: Optional[str] = None,
        viewport: Optional[Dict[str, int]] = None,
        enable_har: bool = False,
        enable_screenshots: bool = True,
        screenshot_dir: Optional[str] = None,
        enable_stealth: bool = True,
    ):
        """Initialize Playwright engine.

        Args:
            config: Engine configuration
            browser_type: Browser type ('chromium', 'firefox', 'webkit')
            headless: Run browser in headless mode
            user_agent: Custom user agent
            viewport: Viewport size {'width': 1920, 'height': 1080}
            enable_har: Enable HAR recording
            enable_screenshots: Enable screenshot capture
            screenshot_dir: Directory for screenshots
            enable_stealth: Enable anti-detection features
        """
        super().__init__(config)

        self.browser_type = browser_type
        self.headless = headless
        self.user_agent = user_agent
        self.viewport = viewport or {"width": 1920, "height": 1080}
        self.enable_har = enable_har
        self.enable_screenshots = enable_screenshots
        self.screenshot_dir = Path(screenshot_dir or "./data/screenshots")
        self.enable_stealth = enable_stealth

        # Lazy initialization
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._loop = None

        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_initialized(self) -> None:
        """Ensure Playwright is initialized (lazy init)."""
        if self._playwright is not None:
            return

        try:
            from playwright.sync_api import sync_playwright

            self._playwright = sync_playwright().start()

            # Select browser
            if self.browser_type == "chromium":
                browser_launcher = self._playwright.chromium
            elif self.browser_type == "firefox":
                browser_launcher = self._playwright.firefox
            elif self.browser_type == "webkit":
                browser_launcher = self._playwright.webkit
            else:
                raise ValueError(f"Unsupported browser type: {self.browser_type}")

            # Launch browser
            launch_options = {
                "headless": self.headless,
                "proxy": {"server": self.config.proxy} if self.config.proxy else None,
            }

            self._browser = browser_launcher.launch(**launch_options)

            # Create context
            context_options = {
                "viewport": self.viewport,
                "user_agent": self.user_agent or self._get_default_user_agent(),
                "ignore_https_errors": True,
                "record_har_path": str(self.screenshot_dir / "network.har")
                if self.enable_har
                else None,
            }

            self._context = self._browser.new_context(**context_options)

            # Apply stealth settings
            if self.enable_stealth:
                self._apply_stealth_settings()

            # Create page
            self._page = self._context.new_page()

            log.info(
                f"Playwright initialized: browser={self.browser_type}, headless={self.headless}"
            )

        except ImportError:
            raise EngineError(
                "Playwright not installed. Install with: pip install playwright && playwright install"
            )
        except Exception as e:
            log.error(f"Failed to initialize Playwright: {e}", exc_info=True)
            raise EngineError(f"Playwright initialization failed: {e}")

    def _apply_stealth_settings(self) -> None:
        """Apply anti-detection settings to context."""
        if not self._context:
            return

        try:
            # Add init script to mask automation
            self._context.add_init_script("""
                // Remove webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                // Mock permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );

                // Mock plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });

                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            """)

            log.debug("Applied stealth settings to browser context")

        except Exception as e:
            log.warning(f"Failed to apply stealth settings: {e}")

    def _get_default_user_agent(self) -> str:
        """Get default user agent string."""
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

    def fetch(
        self,
        url: str,
        *,
        wait_until: str = "domcontentloaded",
        wait_for_selector: Optional[str] = None,
        wait_for_timeout: Optional[int] = None,
        screenshot_name: Optional[str] = None,
        execute_script: Optional[str] = None,
        **kwargs: Any,
    ) -> EngineResult:
        """Fetch content from URL using Playwright.

        Args:
            url: Target URL
            wait_until: Wait until ('load', 'domcontentloaded', 'networkidle')
            wait_for_selector: CSS selector to wait for
            wait_for_timeout: Additional timeout in ms after page load
            screenshot_name: Optional screenshot filename
            execute_script: Optional JavaScript to execute
            **kwargs: Additional Playwright navigation options

        Returns:
            EngineResult with content and metadata

        Raises:
            EngineError on failure
            RateLimitError if rate limited
        """
        self._ensure_initialized()

        if self._closed:
            raise EngineError("Engine is closed")

        start_time = time.time()
        safe_log(log, "info", "Fetching URL with Playwright", extra=sanitize_for_log({"url": url}))

        # Apply rate limiting
        if self.config.rate_limiter:
            self.config.rate_limiter.wait_if_needed()

        # Execute with retries
        last_error = None
        for attempt in range(self.config.max_retries + 1):
            try:
                # Navigate to URL
                response = self._page.goto(
                    url,
                    wait_until=wait_until,
                    timeout=self.config.timeout * 1000,
                    **kwargs,
                )

                # Check for rate limiting
                status_code = response.status if response else 200
                if status_code == 429:
                    raise RateLimitError(
                        "Rate limited (429)", url=url, status_code=429
                    )

                # Wait for selector if specified
                if wait_for_selector:
                    self._page.wait_for_selector(
                        wait_for_selector, timeout=self.config.timeout * 1000
                    )

                # Additional timeout
                if wait_for_timeout:
                    self._page.wait_for_timeout(wait_for_timeout)

                # Execute script if specified
                script_result = None
                if execute_script:
                    script_result = self._page.evaluate(execute_script)

                # Get content
                content = self._page.content()

                # Check for rate limiting in content
                if self._detect_rate_limit(content):
                    raise RateLimitError(
                        "Rate limit detected in content", url=url, status_code=status_code
                    )

                # Take screenshot
                screenshot_path = None
                if self.enable_screenshots:
                    screenshot_path = self._take_screenshot(screenshot_name or f"fetch_{int(time.time())}")

                # Get headers
                headers = response.all_headers() if response else {}

                # Build metadata
                metadata = {
                    "browser_type": self.browser_type,
                    "headless": self.headless,
                    "screenshot_path": str(screenshot_path) if screenshot_path else None,
                    "script_result": script_result,
                    "url": self._page.url,  # Final URL after redirects
                }

                elapsed = time.time() - start_time

                safe_log(
                    log,
                    "info",
                    "Successfully fetched URL",
                    extra=sanitize_for_log({"url": url, "elapsed": f"{elapsed:.2f}s"}),
                )

                return EngineResult(
                    url=url,
                    status_code=status_code,
                    content=content,
                    headers=headers,
                    elapsed_seconds=elapsed,
                    metadata=metadata,
                )

            except RateLimitError:
                raise  # Don't retry rate limits

            except Exception as e:
                last_error = e
                safe_log(
                    log,
                    "warning",
                    "Fetch attempt failed",
                    extra=sanitize_for_log({
                        "url": url,
                        "attempt": attempt + 1,
                        "max_retries": self.config.max_retries,
                        "error": str(e),
                    }),
                )

                if attempt < self.config.max_retries:
                    # Calculate backoff with jitter
                    import random
                    backoff = self.config.retry_backoff * (attempt + 1)
                    jitter = random.uniform(0, self.config.retry_jitter)
                    delay = backoff + jitter

                    safe_log(
                        log,
                        "info",
                        "Retrying after backoff",
                        extra=sanitize_for_log({"delay": f"{delay:.2f}s"}),
                    )
                    time.sleep(delay)
                else:
                    break

        # All retries exhausted
        error_msg = f"Failed to fetch {url} after {self.config.max_retries + 1} attempts: {last_error}"
        log.error(error_msg)
        raise EngineError(error_msg, url=url, retries_exhausted=True)

    def _detect_rate_limit(self, content: str) -> bool:
        """Detect rate limiting in page content.

        Args:
            content: HTML content

        Returns:
            True if rate limiting detected
        """
        if not content:
            return False

        content_lower = content.lower()
        rate_limit_indicators = [
            "too many requests",
            "rate limit",
            "slow down",
            "try again later",
            "temporarily blocked",
        ]

        return any(indicator in content_lower for indicator in rate_limit_indicators)

    def _take_screenshot(self, name: str) -> Optional[Path]:
        """Take screenshot of current page.

        Args:
            name: Screenshot name (without extension)

        Returns:
            Path to screenshot file or None if failed
        """
        if not self._page:
            return None

        try:
            screenshot_path = self.screenshot_dir / f"{name}.png"
            self._page.screenshot(path=str(screenshot_path), full_page=True)
            log.debug(f"Screenshot saved: {screenshot_path}")
            return screenshot_path

        except Exception as e:
            log.warning(f"Failed to take screenshot: {e}")
            return None

    def execute_script(self, script: str) -> Any:
        """Execute JavaScript on current page.

        Args:
            script: JavaScript code to execute

        Returns:
            Script result
        """
        self._ensure_initialized()

        if not self._page:
            raise EngineError("No active page")

        try:
            result = self._page.evaluate(script)
            return result
        except Exception as e:
            raise EngineError(f"Script execution failed: {e}")

    def get_cookies(self) -> list:
        """Get all cookies from current context.

        Returns:
            List of cookie dictionaries
        """
        self._ensure_initialized()

        if not self._context:
            raise EngineError("No active context")

        try:
            cookies = self._context.cookies()
            return cookies
        except Exception as e:
            log.warning(f"Failed to get cookies: {e}")
            return []

    def set_cookies(self, cookies: list) -> None:
        """Set cookies in current context.

        Args:
            cookies: List of cookie dictionaries
        """
        self._ensure_initialized()

        if not self._context:
            raise EngineError("No active context")

        try:
            self._context.add_cookies(cookies)
            log.debug(f"Set {len(cookies)} cookies")
        except Exception as e:
            log.warning(f"Failed to set cookies: {e}")

    def cleanup(self) -> None:
        """Clean up Playwright resources."""
        if self._closed:
            return

        try:
            if self._page:
                self._page.close()
                self._page = None

            if self._context:
                self._context.close()
                self._context = None

            if self._browser:
                self._browser.close()
                self._browser = None

            if self._playwright:
                self._playwright.stop()
                self._playwright = None

            self._closed = True
            log.info("Playwright engine cleaned up")

        except Exception as e:
            log.warning(f"Error during Playwright cleanup: {e}")

    def __enter__(self):
        """Context manager entry."""
        self._ensure_initialized()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()

    def __del__(self):
        """Destructor."""
        self.cleanup()


class AsyncPlaywrightEngine(BaseEngine):
    """
    Async version of Playwright engine for high-concurrency scenarios.

    This version uses async Playwright API for better performance
    when handling multiple concurrent requests.
    """

    def __init__(self, config: EngineConfig, **kwargs):
        """Initialize async Playwright engine.

        Args:
            config: Engine configuration
            **kwargs: Same options as PlaywrightEngine
        """
        super().__init__(config)
        self.sync_engine = PlaywrightEngine(config, **kwargs)

    async def fetch_async(self, url: str, **kwargs: Any) -> EngineResult:
        """Async fetch operation.

        Args:
            url: Target URL
            **kwargs: Additional fetch options

        Returns:
            EngineResult
        """
        # Run sync fetch in executor to avoid blocking
        import concurrent.futures

        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            result = await loop.run_in_executor(
                pool, lambda: self.sync_engine.fetch(url, **kwargs)
            )
        return result

    def fetch(self, url: str, **kwargs: Any) -> EngineResult:
        """Sync fetch (delegates to sync engine).

        Args:
            url: Target URL
            **kwargs: Additional fetch options

        Returns:
            EngineResult
        """
        return self.sync_engine.fetch(url, **kwargs)

    def cleanup(self) -> None:
        """Clean up resources."""
        self.sync_engine.cleanup()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
