"""
LAFA scraper pipeline.

This is a stub implementation. Use tools/add_scraper_advanced.py to scaffold
a full implementation.
"""

import csv
from datetime import date
from pathlib import Path
from typing import List, Optional

from src.common.config_loader import load_source_config
from src.common.logging_utils import get_logger, sanitize_for_log, safe_log
from src.common.paths import OUTPUT_DIR
from src.engines.selenium_engine import open_with_session
from src.processors.dedupe import dedupe_records
from src.processors.qc_rules import is_valid
from src.processors.unify_fields import unify_record
from src.resource_manager import ResourceManager, get_default_resource_manager
from src.sessions.session_manager import create_session_record

log = get_logger("lafa-pipeline")


def ensure_logged_in(driver) -> None:
    """Login stub for LAFA."""
    log.info("ensure_logged_in: stub (no actual login)")


def fetch_item_urls(driver) -> List[str]:
    """Fetch list of URLs to scrape (stub)."""
    log.info("Fetching item URLs for LAFA (stub)")
    return []


def extract_item(driver, url: str) -> dict:
    """Extract a single item from detail page (stub)."""
    safe_log(log, "info", "Extracting item for LAFA (stub)", extra=sanitize_for_log({"url": url}))
    return {
        "item_url": url,
        "name": f"Dummy item at {url}",
        "price": 100.0,
        "currency": "USD",
        "source": "lafa",
    }


def run_lafa(resource_manager: Optional[ResourceManager] = None) -> Path:
    """End-to-end pipeline for LAFA."""
    source_name = "lafa"
    log.info("Starting LAFA pipeline run")

    # Load config to get base_url
    source_config = load_source_config(source_name)
    base_url = source_config.get("base_url") or "https://example.com"
    if base_url == "https://example.com":
        log.warning("LAFA is using placeholder URL. Update config/sources/lafa.yaml with real base_url.")

    resource_manager = resource_manager or get_default_resource_manager()

    account_key, username, password = resource_manager.account_router.acquire_account(source_name)
    proxy = resource_manager.proxy_pool.choose_proxy(source_name) or ""
    account_id = account_key.split(":", 1)[1]

    session_record = create_session_record(source_name, account_id, proxy)
    browser_session = open_with_session(base_url, session_record)
    driver = browser_session.driver

    try:
        ensure_logged_in(driver)
        driver.get(base_url)

        item_urls = fetch_item_urls(driver)
        all_records: List[dict] = []

        for url in item_urls:
            driver.get(url)
            raw = extract_item(driver, url)
            unified = unify_record(raw)
            if is_valid(unified):
                all_records.append(unified)

        daily_dir = OUTPUT_DIR / "lafa" / "daily"
        daily_dir.mkdir(parents=True, exist_ok=True)
        out_path = daily_dir / f"lafa_snapshot_{date.today().isoformat()}.csv"

        if all_records:
            deduped_records = dedupe_records(all_records)
            dropped = len(all_records) - len(deduped_records)
            if dropped:
                log.info("Dropped %d duplicate records before writing", dropped)
            all_records = deduped_records

            with out_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["product_url", "name", "price", "currency", "company", "source"],
                )
                writer.writeheader()
                writer.writerows(all_records)
            log.info("Wrote %d records to %s", len(all_records), out_path)
        else:
            log.warning("No valid records to write for LAFA run.")

        return out_path
    finally:
        browser_session.quit()
        resource_manager.account_router.release_account(account_key)


def main():
    """Main entry point for LAFA pipeline."""
    out_path = run_lafa()
    log.info("Completed LAFA pipeline run. Output: %s", out_path)


if __name__ == "__main__":
    main()
