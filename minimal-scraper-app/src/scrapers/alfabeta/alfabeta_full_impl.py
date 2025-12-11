import re
from pathlib import Path
from typing import Dict, Optional

from bs4 import BeautifulSoup
from selenium.webdriver.remote.webdriver import WebDriver

from src.common.logging_utils import get_logger, sanitize_for_log, safe_log

log = get_logger("alfabeta-full-impl")

SAMPLE_PATH = Path(__file__).parent / "samples" / "details_sample.html"


def _load_html(driver: WebDriver) -> str:
    html = getattr(driver, "page_source", "") or ""
    if html:
        return html
    if SAMPLE_PATH.exists():
        return SAMPLE_PATH.read_text(encoding="utf-8")
    return ""


def _parse_price(text: str) -> Optional[float]:
    match = re.search(r"([0-9]+(?:[.,][0-9]+)?)", text or "")
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


def extract_product(
    driver: WebDriver,
    url: str,
    selectors: Optional[Dict[str, str]] = None,
    run_id: Optional[str] = None,
) -> Dict:
    """Extract product data from a product detail page."""

    selectors = selectors or {}
    name_sel = selectors.get("product_name_selector", "h1.product-name")
    lab_sel = selectors.get("lab_name_selector", "div.lab-name")
    presentation_sel = selectors.get("presentation_selector", "div.presentation")
    price_sel = selectors.get("price_selector", "div.price")
    currency_hint = selectors.get("currency_hint", "ARS")

    html = _load_html(driver)
    soup = BeautifulSoup(html, "lxml")

    def _text(selector: str) -> Optional[str]:
        node = soup.select_one(selector)
        if not node:
            return None
        return node.get_text(strip=True)

    name = _text(name_sel)
    lab = _text(lab_sel)
    presentation = _text(presentation_sel)
    price_raw = _text(price_sel)
    price = _parse_price(price_raw) if price_raw else None

    record = {
        "product_url": url,
        "name": name,
        "lab_name": lab,
        "presentation_raw": presentation,
        "price": price,
        "currency": currency_hint,
        "company": lab,
        "scrape_run_id": run_id,
    }

    missing = [k for k, v in record.items() if v in (None, "") and k in {"name", "price"}]
    if missing:
        safe_log(
            log,
            "warning",
            "Missing critical fields for product",
            extra=sanitize_for_log({"missing": missing, "product_url": url}),
        )
    else:
        log.info("Extracted product %s", name)
    return record
