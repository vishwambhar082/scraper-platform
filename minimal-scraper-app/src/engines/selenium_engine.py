import os
import random
import time
from typing import Mapping, Optional

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from src.common.logging_utils import get_logger, sanitize_for_log, safe_log
from src.sessions.session_manager import SessionRecord

log = get_logger("selenium-engine")
FAKE_BROWSER_ENV = "SCRAPER_PLATFORM_FAKE_BROWSER"
CHROMEDRIVER_PATH_ENV = "SCRAPER_PLATFORM_CHROMEDRIVER_PATH"

# Cache the resolved chromedriver path so we don't repeatedly call
# ChromeDriverManager().install(), which is relatively expensive.
_CHROMEDRIVER_PATH: Optional[str] = None
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 1.0
DEFAULT_JITTER = 0.5
DEFAULT_WAIT = 0.25


class FakeDriver:
    def __init__(self):
        self._cookies = []
        self.current_url = ""

    def set_window_size(self, *_args, **_kwargs):
        return None

    def get(self, url: str):
        self.current_url = url

    def add_cookie(self, cookie):
        self._cookies.append(cookie)

    def get_cookies(self):
        return list(self._cookies)

    def quit(self):
        """Quit the fake driver (no-op)."""
        return None


class BrowserSession:
    """Browser session wrapper that manages driver lifecycle and cookie persistence."""

    def __init__(self, driver, session_record: Optional[SessionRecord] = None, proxy: Optional[str] = None):
        self.driver = driver
        self.session_record = session_record
        self.proxy = proxy

    def quit(self):
        try:
            if self.session_record:
                self.session_record.save_cookies(self.driver)
        finally:
            self.driver.quit()

    def _recreate_driver(self, proxy: Optional[str]):
        try:
            self.driver.quit()
        except Exception:  # pragma: no cover - defensive cleanup
            pass

        self.driver = create_driver(proxy)
        self.proxy = proxy
        if self.session_record:
            self.session_record.try_restore_cookies(self.driver)

    def navigate(
        self,
        url: str,
        retries: int = DEFAULT_RETRIES,
        backoff: float = DEFAULT_BACKOFF,
        jitter: float = DEFAULT_JITTER,
        allow_proxy_fallback: bool = True,
        wait: float = DEFAULT_WAIT,
    ):
        """Navigate with retry, jitter, and optional proxy failover."""

        attempt = 0
        last_exc: Optional[Exception] = None

        while attempt < retries:
            try:
                self.driver.get(url)
                if _looks_rate_limited(self.driver):
                    raise WebDriverException("rate limited or blocked")
                _sleep_with_jitter(wait, jitter)
                return
            except Exception as exc:  # pragma: no cover - guarded retries
                last_exc = exc
                attempt += 1

                if allow_proxy_fallback and self.proxy and attempt == retries // 2:
                    safe_log(
                        log,
                        "warning",
                        "Proxy appears unhealthy; recreating driver without proxy",
                        extra=sanitize_for_log({"url": url}),
                    )
                    self._recreate_driver(proxy=None)

                if attempt >= retries:
                    break

                delay = _jitter_delay(backoff * attempt, jitter)
                safe_log(
                    log,
                    "info",
                    "Retrying navigation",
                    extra=sanitize_for_log({"url": url, "attempt": attempt, "delay": delay}),
                )
                time.sleep(delay)

        if last_exc:
            raise last_exc

def _use_fake_driver() -> bool:
    """Check if fake driver mode is enabled via environment variable."""
    return os.getenv(FAKE_BROWSER_ENV, "").lower() in {"1", "true", "yes", "on"}


def _get_chromedriver_path() -> str:
    """
    Resolve the chromedriver executable path.

    Priority:
    1. SCRAPER_PLATFORM_CHROMEDRIVER_PATH env var, if set.
    2. Cached result of ChromeDriverManager().install().
    """
    global _CHROMEDRIVER_PATH

    # Explicit override from env
    env_path = os.getenv(CHROMEDRIVER_PATH_ENV)
    if env_path:
        return env_path

    if _CHROMEDRIVER_PATH is None:
        _CHROMEDRIVER_PATH = ChromeDriverManager().install()
        log.info("Resolved chromedriver via ChromeDriverManager: %s", _CHROMEDRIVER_PATH)
    return _CHROMEDRIVER_PATH


def _is_rate_limited(
    html: str,
    status_code: Optional[int] = None,
    headers: Optional[Mapping[str, str]] = None,
) -> bool:
    """Best-effort rate-limit detection using status codes, headers, and body text."""

    if status_code is not None and status_code in (429, 503):
        return True

    if headers:
        ratelimit_hdr = headers.get("X-RateLimit-Remaining")
        if ratelimit_hdr is not None:
            try:
                remaining = int(ratelimit_hdr)
                if remaining <= 0:
                    return True
            except ValueError:
                pass

    text = html.lower()
    return "rate limit" in text or "too many requests" in text


def _looks_rate_limited(driver) -> bool:
    """Best-effort rate limit detection using driver state."""

    page_source = getattr(driver, "page_source", "") or ""
    current_url = getattr(driver, "current_url", "") or ""
    status_code = getattr(driver, "status_code", None)

    headers = None
    response = getattr(driver, "last_response", None)
    if response:
        status_code = getattr(response, "status_code", status_code)
        headers = getattr(response, "headers", None)

    haystack = f"{page_source} {current_url}"
    return _is_rate_limited(haystack, status_code=status_code, headers=headers)


def _jitter_delay(base: float, jitter: float) -> float:
    return max(0.0, base + random.uniform(0, jitter))


def _sleep_with_jitter(delay: float, jitter: float) -> None:
    delay = _jitter_delay(delay, jitter)
    if delay > 0:
        time.sleep(delay)


def create_driver(proxy: Optional[str] = None):
    """Create a Selenium WebDriver instance (real or fake based on environment)."""
    if _use_fake_driver():
        log.info("Using FakeDriver (env %s)", FAKE_BROWSER_ENV)
        return FakeDriver()

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    if proxy:
        opts.add_argument(f"--proxy-server=http://{proxy}")

    driver_path = _get_chromedriver_path()
    driver = webdriver.Chrome(service=Service(driver_path), options=opts)
    driver.set_window_size(1280, 800)
    return driver


def open_with_session(url: str, session_record: SessionRecord) -> BrowserSession:
    """Open a browser session with cookie restoration."""
    proxy = session_record.proxy_id or None
    driver = create_driver(proxy)
    parts = url.split("/")
    base = parts[0] + "//" + parts[2]
    browser_session = BrowserSession(driver, session_record, proxy=proxy)
    browser_session.navigate(base)
    session_record.try_restore_cookies(driver)
    browser_session.navigate(url)
    return browser_session
