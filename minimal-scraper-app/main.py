#!/usr/bin/env python3
"""
Simplified Desktop Scraper Application

This is a standalone application that can run scrapers locally without
needing Airflow, Docker, or other complex infrastructure.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

# Add src to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.common.config_loader import load_config, load_source_config
# from src.common.logging_utils import get_logger
from simple_logging_config import get_simple_logger as get_logger
from src.common.paths import OUTPUT_DIR
from src.engines.engine_factory import create_engine
from src.resource_manager import get_default_resource_manager
from src.sessions.session_manager import create_session_record

# Setup logging
log = get_logger("desktop-scraper")

def run_scraper(source_name: str, env: str = "dev") -> None:
    """
    Run a scraper locally.
    
    Args:
        source_name: Name of the scraper to run (e.g., 'alfabeta', 'template')
        env: Environment to use ('dev', 'staging', 'prod')
    """
    log.info(f"Starting scraper: {source_name}")
    
    try:
        # Load configurations
        platform_config = load_config(env)
        source_config = load_source_config(source_name)
        
        # Get engine type
        engine_type = source_config.get("engine", {}).get("type", "http")
        log.info(f"Using engine: {engine_type}")
        
        # Create resource manager
        resource_manager = get_default_resource_manager()
        
        # Acquire account and proxy
        try:
            account_key, username, password = resource_manager.account_router.acquire_account(source_name)
            proxy = resource_manager.proxy_pool.choose_proxy(source_name) or ""
            account_id = account_key.split(":", 1)[1]
        except Exception as e:
            log.warning(f"Could not acquire account/proxy: {e}")
            account_key, username, password, proxy, account_id = "", "", "", "", "local"
        
        # Create session record
        session_record = create_session_record(source_name, account_id, proxy)
        
        # Get base URL
        base_url = source_config.get("base_url", "https://example.com")
        log.info(f"Scraping URL: {base_url}")
        
        # Create engine
        engine = create_engine(engine_type, source_config, proxy=proxy, session_record=session_record)
        
        try:
            # For simple HTTP scrapers, we can just fetch the base URL
            if hasattr(engine, 'fetch'):
                result = engine.fetch(base_url)
                log.info(f"Successfully fetched {len(result.content)} bytes")
                
                # Save result to file
                output_dir = OUTPUT_DIR / source_name
                output_dir.mkdir(parents=True, exist_ok=True)
                
                output_file = output_dir / f"{source_name}_output.html"
                output_file.write_text(result.content, encoding="utf-8")
                log.info(f"Saved output to: {output_file}")
                
            # For browser-based scrapers, we might need to call specific functions
            else:
                log.warning(f"Engine {engine_type} doesn't support simple fetch. You may need to implement specific scraper logic.")
                
        finally:
            # Cleanup
            if hasattr(engine, 'cleanup'):
                engine.cleanup()
            
            # Release account
            try:
                if account_key:
                    resource_manager.account_router.release_account(account_key)
            except Exception as e:
                log.warning(f"Could not release account: {e}")
                
    except Exception as e:
        log.error(f"Error running scraper: {e}", exc_info=True)
        raise

def list_scrapers() -> None:
    """List available scrapers."""
    scrapers_dir = Path(__file__).parent / "src" / "scrapers"
    if not scrapers_dir.exists():
        log.error("Scrapers directory not found")
        return
        
    print("Available scrapers:")
    for item in scrapers_dir.iterdir():
        if item.is_dir() and not item.name.startswith("__"):
            print(f"  - {item.name}")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Desktop Scraper Application")
    parser.add_argument("--source", help="Source name to scrape (e.g., alfabeta, template)")
    parser.add_argument("--env", default="dev", help="Environment (dev, staging, prod)")
    parser.add_argument("--list", action="store_true", help="List available scrapers")
    
    args = parser.parse_args()
    
    if args.list:
        list_scrapers()
        return
    
    if not args.source:
        print("Error: --source is required")
        parser.print_help()
        sys.exit(1)
        
    try:
        run_scraper(args.source, args.env)
        print("Scraping completed successfully!")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()