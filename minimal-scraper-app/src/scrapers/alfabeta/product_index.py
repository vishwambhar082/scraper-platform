from pathlib import Path
from typing import Dict, List, Optional

from bs4 import BeautifulSoup
from selenium.webdriver.remote.webdriver import WebDriver
from urllib.parse import urljoin

from src.common.logging_utils import get_logger, sanitize_for_log, safe_log

log = get_logger("alfabeta-product-index")

SAMPLE_PATH = Path(__file__).parent / "samples" / "product_list_sample.html"


def _load_html(driver: WebDriver) -> str:
    html = getattr(driver, "page_source", "") or ""
    if html:
        return html
    if SAMPLE_PATH.exists():
        return SAMPLE_PATH.read_text(encoding="utf-8")
    return ""


def fetch_product_urls(
    driver: WebDriver,
    company_url: str,
    selectors: Optional[Dict[str, str]] = None,
    run_id: Optional[str] = None,
) -> List[str]:
    """Fetch list of product URLs for a given company."""

    selectors = selectors or {}
    product_selector = selectors.get("product_link_selector", "a.product-link")
    safe_log(
        log,
        "info",
        "Fetching product URLs",
        extra=sanitize_for_log(
            {"run_id": run_id, "company_url": company_url, "selector": product_selector}
        ),
    )

    html = _load_html(driver)
    soup = BeautifulSoup(html, "lxml")
    product_links = []

    for a in soup.select(product_selector):
        href = a.get("href")
        if not href:
            continue
        product_links.append(urljoin(company_url, href))

    log.info("Found %d product URLs for company", len(product_links))
    return product_links
