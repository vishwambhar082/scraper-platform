from pathlib import Path
from typing import Dict, List, Optional

from bs4 import BeautifulSoup
from selenium.webdriver.remote.webdriver import WebDriver
from urllib.parse import urljoin

from src.common.logging_utils import get_logger, sanitize_for_log, safe_log

log = get_logger("alfabeta-company-index")

SAMPLE_PATH = Path(__file__).parent / "samples" / "listing_sample.html"


def _load_html(driver: WebDriver) -> str:
    html = getattr(driver, "page_source", "") or ""
    if html:
        return html
    if SAMPLE_PATH.exists():
        return SAMPLE_PATH.read_text(encoding="utf-8")
    return ""


def fetch_company_urls(
    driver: WebDriver,
    base_url: str,
    selectors: Optional[Dict[str, str]] = None,
    run_id: Optional[str] = None,
) -> List[str]:
    """Fetch list of company URLs from the index page.

    Falls back to sample HTML when running with the fake driver so the pipeline
    remains testable offline.
    """

    selectors = selectors or {}
    company_selector = selectors.get("company_link_selector", "a.company-link")
    safe_log(
        log,
        "info",
        "Fetching company URLs",
        extra=sanitize_for_log(
            {"run_id": run_id, "base_url": base_url, "selector": company_selector}
        ),
    )

    html = _load_html(driver)
    soup = BeautifulSoup(html, "lxml")
    company_links = []

    for a in soup.select(company_selector):
        href = a.get("href")
        if not href:
            continue
        company_links.append(urljoin(base_url, href))

    log.info("Found %d company URLs", len(company_links))
    return company_links
