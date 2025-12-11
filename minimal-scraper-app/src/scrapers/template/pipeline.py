"""
Template scraper pipeline.

This is a template used by tools/add_scraper_advanced.py to scaffold
new scrapers. Do not modify this file directly.

NOTE: This is a TEMPLATE-ONLY scraper for scaffolding new sources.
It uses example.com as a placeholder and should not be run in production.
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

log = get_logger("template-pipeline")


def ensure_logged_in(driver) -> None:
    """Login stub for template."""
    log.info("ensure_logged_in: stub (no actual login)")


def fetch_item_urls(driver) -> List[str]:
    """Fetch list of URLs to scrape (stub)."""
    log.info("Fetching item URLs for template (stub)")
    return []


def extract_item(driver, url: str) -> dict:
    """Extract a single item from detail page (stub)."""
    safe_log(log, "info", "Extracting item for template (stub)", extra=sanitize_for_log({"url": url}))
    return {
        "item_url": url,
        "name": f"Dummy item at {url}",
        "price": 100.0,
        "currency": "USD",
        "source": "template",
    }


def run_template(resource_manager: Optional[ResourceManager] = None) -> Path:
    """
    End-to-end pipeline for template.
    
    WARNING: This is a TEMPLATE-ONLY scraper for scaffolding new sources.
    Do not run this in production. It uses example.com as a placeholder.
    """
    source_name = "template"
    log.warning("Running TEMPLATE scraper - this is for scaffolding only, not production use")
    log.info("Starting template pipeline run")

    # Load config to get base_url (will be example.com for template)
    source_config = load_source_config(source_name)
    base_url = source_config.get("base_url") or "https://example.com"
    if base_url == "https://example.com":
        log.warning("Template scraper using placeholder URL. This is expected for template-only usage.")

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

        daily_dir = OUTPUT_DIR / "template" / "daily"
        daily_dir.mkdir(parents=True, exist_ok=True)
        out_path = daily_dir / f"template_snapshot_{date.today().isoformat()}.csv"

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
            log.warning("No valid records to write for template run.")

        return out_path
    finally:
        browser_session.quit()
        resource_manager.account_router.release_account(account_key)


def main():
    """Main entry point for template pipeline."""
    out_path = run_template()
    log.info("Completed template pipeline run. Output: %s", out_path)


if __name__ == "__main__":
    main()
