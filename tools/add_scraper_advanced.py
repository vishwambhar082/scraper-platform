"""
add_scraper_advanced.py
---------------------------------
Scaffold a new scraper:

- src/scrapers/{source}/__init__.py
- src/scrapers/{source}/pipeline.py
- config/sources/{source}.yaml
- dags/scraper_{source}.py

Usage (from project root):

    python -m tools.add_scraper_advanced mynewscraper

Optional:

    python -m tools.add_scraper_advanced mynewscraper --requires-login --engine selenium
    python -m tools.add_scraper_advanced mynewscraper --interactive
"""

import argparse
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
import textwrap
from typing import Optional
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def validate_url(url: str) -> bool:
    """Validate URL format."""
    try:
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except Exception:
        return False


def prompt_user(prompt: str, default: Optional[str] = None, validator: Optional[callable] = None) -> str:
    """Interactive prompt with validation."""
    while True:
        if default:
            response = input(f"{prompt} [{default}]: ").strip()
            if not response:
                response = default
        else:
            response = input(f"{prompt}: ").strip()
        
        if validator:
            if validator(response):
                return response
            print(f"Invalid input. Please try again.")
        else:
            if response:
                return response
            print("Input cannot be empty. Please try again.")


def collect_scraper_config(
    source: str,
    engine: str,
    requires_login: bool,
    interactive: bool,
    base_url: Optional[str] = None,
    login_url: Optional[str] = None,
    username_prefix: Optional[str] = None,
    password_prefix: Optional[str] = None,
) -> dict:
    """Collect scraper configuration from user or use defaults."""
    config = {
        "base_url": base_url or "",
        "login_url": login_url or "",
        "username_env_prefix": username_prefix or f"{source.upper()}_USER_",
        "password_env_prefix": password_prefix or f"{source.upper()}_PASS_",
    }

    if not interactive and not config["base_url"]:
        raise SystemExit(
            "Missing base URL. Provide --base-url or run with --interactive to enter values."
        )
    
    if interactive:
        print(f"\n{'='*60}")
        print(f"Configuring scraper: {source}")
        print(f"{'='*60}\n")
        
        # Base URL
        config["base_url"] = prompt_user(
            "Enter base URL for the scraper",
            default=config["base_url"] or "https://",
            validator=validate_url
        )

        # Login URL (if login required)
        if requires_login:
            config["login_url"] = prompt_user(
                "Enter login page URL",
                default=(config["base_url"] + "/login") if config["base_url"] else "https://",
                validator=validate_url
            )
            
            # Environment variable prefixes
            config["username_env_prefix"] = prompt_user(
                "Enter username environment variable prefix",
                default=config["username_env_prefix"]
            )
            
            config["password_env_prefix"] = prompt_user(
                "Enter password environment variable prefix",
                default=config["password_env_prefix"]
            )
        
        print(f"\n✓ Configuration collected\n")
    
    # Non-interactive defaults
    if not interactive:
        config["base_url"] = config["base_url"] or ""
        if requires_login:
            config["login_url"] = config["login_url"] or (config["base_url"].rstrip("/") + "/login")

    return config


def create_scraper_package(source: str, engine: str, requires_login: bool, config: dict) -> None:
    scraper_dir = PROJECT_ROOT / "src" / "scrapers" / source
    scraper_dir.mkdir(parents=True, exist_ok=True)

    init_path = scraper_dir / "__init__.py"
    if not init_path.exists():
        init_path.write_text("", encoding="utf-8")

    pipeline_path = scraper_dir / "pipeline.py"
    if pipeline_path.exists():
        print(f"[WARN] pipeline.py already exists for {source}, skipping.")
        return

    login_comment = "true" if requires_login else "false"
    
    # Extract config values for template
    base_url_val = config['base_url']
    login_url_val = config['login_url']
    username_prefix_val = config['username_env_prefix']
    password_prefix_val = config['password_env_prefix']

    pipeline_code = f"""
    import csv
    import json
    import os
    from datetime import date
    from pathlib import Path
    from typing import List, Optional

    from src.common.config_loader import load_source_config
    from src.common.paths import OUTPUT_DIR
    from src.common.logging_utils import get_logger
    from src.resource_manager.account_router import acquire_account, release_account
    from src.resource_manager.proxy_router import pick_healthy_proxy
    from src.sessions.session_manager import create_session_record
    from src.engines.selenium_engine import open_with_session
    from src.processors.dedupe import dedupe_records
    from src.processors.unify_fields import unify_record
    from src.processors.qc_rules import is_valid

    log = get_logger("{source}-pipeline")

    # Base URL from config - validated during setup
    BASE_URL = "{base_url_val}"


    def ensure_logged_in(driver, source_config: dict) -> None:
        \"\"\"
        Handle login for {source} if required.

        requires_login = {login_comment}
        
        Implementation:
          1. Check if already logged in (look for logout button or user menu)
          2. If not, navigate to login_url from config
          3. Enter username/password from env variables
          4. Submit and verify login success
          5. Handle 2FA if required
        
        Config keys:
          - auth.login_url: Login page URL
          - auth.username_env_prefix: Environment variable prefix for usernames
          - auth.password_env_prefix: Environment variable prefix for passwords
        \"\"\"
        if not source_config.get("auth", {{}}).get("requires_login", False):
            log.info("Login not required for {source}")
            return
        
        import os
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException
        
        auth_config = source_config.get("auth", {{}})
        login_url = auth_config.get("login_url", "{login_url_val}")
        username_prefix = auth_config.get("username_env_prefix", "{username_prefix_val}")
        password_prefix = auth_config.get("password_env_prefix", "{password_prefix_val}")
        
        # Check if already logged in
        try:
            driver.get(BASE_URL)
            # Look for logout button or user menu (customize selector as needed)
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-logout], .user-menu, .logout"))
            )
            log.info("Already logged in to {source}")
            return
        except TimeoutException:
            pass  # Not logged in, proceed with login
        
        # Perform login
        log.info("Logging in to {source}")
        driver.get(login_url)
        
        # Get credentials from environment
        username = os.getenv(f"{{username_prefix}}1")
        password = os.getenv(f"{{password_prefix}}1")
        
        if not username or not password:
            raise ValueError(
                f"Missing credentials. Set {{username_prefix}}1 and {{password_prefix}}1 environment variables."
            )
        
        # Load selectors from selectors.json
        selectors_path = Path(__file__).parent / "selectors.json"
        if selectors_path.exists():
            with open(selectors_path, "r", encoding="utf-8") as f:
                selectors = json.load(f)
            username_selector = selectors.get("username_selector", "input[name='username']")
            password_selector = selectors.get("password_selector", "input[name='password']")
            submit_selector = selectors.get("submit_selector", "button[type='submit']")
        else:
            # Fallback selectors
            username_selector = "input[name='username']"
            password_selector = "input[name='password']"
            submit_selector = "button[type='submit']"
        
        # Enter credentials
        try:
            username_elem = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, username_selector))
            )
            username_elem.clear()
            username_elem.send_keys(username)
            
            password_elem = driver.find_element(By.CSS_SELECTOR, password_selector)
            password_elem.clear()
            password_elem.send_keys(password)
            
            submit_elem = driver.find_element(By.CSS_SELECTOR, submit_selector)
            submit_elem.click()
            
            # Wait for login to complete (redirect or success indicator)
            WebDriverWait(driver, 30).until(
                lambda d: d.current_url != login_url or d.find_elements(By.CSS_SELECTOR, "[data-logout], .user-menu")
            )
            log.info("Login successful for {source}")
        except Exception as exc:
            log.error("Login failed for {source}: %s", exc)
            raise


    def fetch_item_urls(driver, base_url: str) -> List[str]:
        \"\"\"Fetch list of URLs to scrape (listing -> detail pages).
        
        Implementation steps:
          1. Navigate to listing page (e.g., base_url + "/products")
          2. Extract product/item URLs from listing page
          3. Handle pagination if needed
          4. Return list of detail page URLs
        
        Customize this function based on the site's structure.
        \"\"\"
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        # Load selectors from selectors.json
        selectors_path = Path(__file__).parent / "selectors.json"
        if selectors_path.exists():
            with open(selectors_path, "r", encoding="utf-8") as f:
                selectors = json.load(f)
            listing_url = selectors.get("companies_url") or selectors.get("listing_url") or base_url + "/products"
            product_link_selector = selectors.get("product_link_selector", "a.product-link")
        else:
            listing_url = base_url + "/products"
            product_link_selector = "a.product-link"
        
        log.info("Fetching item URLs from %s", listing_url)
        driver.get(listing_url)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, product_link_selector))
        )
        
        # Extract product links
        links = driver.find_elements(By.CSS_SELECTOR, product_link_selector)
        urls = []
        for link in links:
            href = link.get_attribute("href")
            if href:
                # Make absolute URL if relative
                if href.startswith("/"):
                    href = base_url + href
                urls.append(href)
        
        # Handle pagination (implement as needed)
        # Example:
        # next_button = driver.find_elements(By.CSS_SELECTOR, ".next-page")
        # while next_button:
        #     next_button[0].click()
        #     # Extract more URLs...
        
        log.info("Found %d item URLs", len(urls))
        
        if not urls:
            log.warning("No item URLs found. Check selectors and listing page structure.")
            # Return empty list to avoid errors, but log the issue
        
        return urls


    def extract_item(driver, url: str) -> dict:
        \"\"\"Extract a single item from detail page.
        
        Implementation:
          1. Load the detail page (already navigated to url)
          2. Extract fields using selectors from selectors.json
          3. Normalize currency, prices, dates
          4. Return structured dict with required fields
        
        Required fields:
          - product_url (or item_url)
          - name
          - price
          - currency
          - source
        
        Optional fields:
          - company (or lab_name)
          - presentation
          - pcid (if available)
        \"\"\"
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import re
        
        # Load selectors from selectors.json
        selectors_path = Path(__file__).parent / "selectors.json"
        if selectors_path.exists():
            with open(selectors_path, "r", encoding="utf-8") as f:
                selectors = json.load(f)
        else:
            selectors = {{}}
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        record = {{
            "product_url": url,
            "source": "{source}",
        }}
        
        # Extract product name
        name_selector = selectors.get("product_name_selector", "h1.product-name, h1, .product-title")
        try:
            name_elem = driver.find_element(By.CSS_SELECTOR, name_selector)
            record["name"] = name_elem.text.strip()
        except Exception:
            log.warning("Could not extract name from %s", url)
            record["name"] = None
        
        # Extract price
        price_selector = selectors.get("price_selector", ".price, [data-price]")
        try:
            price_elem = driver.find_element(By.CSS_SELECTOR, price_selector)
            price_text = price_elem.text.strip()
            # Extract numeric value
            price_match = re.search(r'[\\d,]+\.?\\d*', price_text.replace(",", ""))
            if price_match:
                record["price"] = float(price_match.group().replace(",", ""))
            else:
                record["price"] = None
        except Exception:
            log.warning("Could not extract price from %s", url)
            record["price"] = None
        
        # Extract currency (from price text or selector)
        currency_hint = selectors.get("currency_hint", "USD")
        try:
            price_elem = driver.find_element(By.CSS_SELECTOR, price_selector)
            price_text = price_elem.text.strip()
            if "$" in price_text or "USD" in price_text:
                record["currency"] = "USD"
            elif "€" in price_text or "EUR" in price_text:
                record["currency"] = "EUR"
            elif "£" in price_text or "GBP" in price_text:
                record["currency"] = "GBP"
            elif "CAD" in price_text:
                record["currency"] = "CAD"
            else:
                record["currency"] = currency_hint
        except Exception:
            record["currency"] = currency_hint
        
        # Extract company/lab name
        lab_selector = selectors.get("lab_name_selector", ".lab-name, .company, [data-company]")
        try:
            lab_elem = driver.find_element(By.CSS_SELECTOR, lab_selector)
            record["company"] = lab_elem.text.strip()
            record["lab_name"] = record["company"]
        except Exception:
            pass  # Optional field
        
        # Extract presentation
        presentation_selector = selectors.get("presentation_selector", ".presentation, [data-presentation]")
        try:
            pres_elem = driver.find_element(By.CSS_SELECTOR, presentation_selector)
            record["presentation"] = pres_elem.text.strip()
        except Exception:
            pass  # Optional field
        
        return record


    def run_{source}(resource_manager: Optional[object] = None) -> Path:
        \"\"\"End-to-end pipeline for {source}.
        
        This is a scaffolded pipeline. You need to implement:
          1. ensure_logged_in() - if requires_login is true
          2. fetch_item_urls() - to get listing URLs
          3. extract_item() - to extract product data from detail pages
        
        The pipeline will:
          - Load config from config/sources/{source}.yaml
          - Use base_url from config (or fallback to example.com with warning)
          - Handle account/proxy allocation
          - Process records through normalization, QC, deduplication
          - Export to CSV
        \"\"\"
        source_name = "{source}"
        log.info("Starting {source} pipeline run")

        # Load configuration
        source_config = load_source_config(source_name)
        base_url = source_config.get("base_url") or source_config.get("urls", {{}}).get("root") or BASE_URL
        
        if base_url == "https://example.com":
            log.error(
                "Invalid base_url: example.com placeholder detected. "
                "Update config/sources/{source}.yaml with real base_url"
            )
            raise ValueError("base_url must be configured with a real URL")

        account_key, username, password = acquire_account(source_name)
        proxy = pick_healthy_proxy(source_name) or ""
        account_id = account_key.split(":", 1)[1]

        session_record = create_session_record(source_name, account_id, proxy)
        browser_session = open_with_session(base_url, session_record)
        driver = browser_session.driver

        try:
            ensure_logged_in(driver, source_config)
            driver.get(base_url)

            item_urls = fetch_item_urls(driver, base_url)
            all_records: List[dict] = []

            for url in item_urls:
                driver.get(url)
                raw = extract_item(driver, url)
                unified = unify_record(raw)
                if is_valid(unified):
                    all_records.append(unified)

            daily_dir = OUTPUT_DIR / "{source}" / "daily"
            daily_dir.mkdir(parents=True, exist_ok=True)
            out_path = daily_dir / f"{source}_snapshot_{{date.today().isoformat()}}.csv"

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
                log.warning("No valid records to write for {source} run.")

            return out_path
        finally:
            browser_session.quit()
            release_account(account_key)


    def main():
        out_path = run_{source}()
        log.info("Completed {source} pipeline run. Output: %s", out_path)


    if __name__ == "__main__":
        main()
    """

    pipeline_path.write_text(textwrap.dedent(pipeline_code).lstrip(), encoding="utf-8")
    print(f"[OK] Created scraper pipeline for {source}: {pipeline_path}")


def create_source_config(source: str, engine: str, requires_login: bool, config: dict) -> None:
    cfg_dir = PROJECT_ROOT / "config" / "sources"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    cfg_path = cfg_dir / f"{source}.yaml"
    if cfg_path.exists():
        print(f"[WARN] Config already exists: {cfg_path}")
        return

    yaml = f"""
    source: {source}

    engine:
      type: {engine}

    # Base URL for the scraper
    base_url: "{base_url_val}"

    auth:
      requires_login: {"true" if requires_login else "false"}
      login_url: "{login_url_val}"
      username_env_prefix: "{username_prefix_val}"
      password_env_prefix: "{password_prefix_val}"

    urls:
      root: "{base_url_val}"  # Alternative location for base_url

    rate_limit:
      min_delay_seconds: 1.0
      max_delay_seconds: 3.0

    output:
      daily_csv_dir: "output/{source}/daily"

    quality:
      require_price: true
      require_name: true

    session:
      sticky_account_proxy: true
      cookie_ttl_hours: 12
    """
    cfg_path.write_text(textwrap.dedent(yaml).lstrip(), encoding="utf-8")
    print(f"[OK] Created source config: {cfg_path}")


def create_selectors_template(source: str, base_url: str) -> None:
    scraper_dir = PROJECT_ROOT / "src" / "scrapers" / source
    scraper_dir.mkdir(parents=True, exist_ok=True)

    selectors_path = scraper_dir / "selectors.json"
    if selectors_path.exists():
        print(f"[WARN] selectors.json already exists: {selectors_path}")
        return

    selectors_json = textwrap.dedent(
        f"""
        {{
          "login_url": "{base_url.rstrip('/') + '/login' if base_url else 'https://example.com/login'}",
          "username_selector": "input[name='username']",
          "password_selector": "input[name='password']",
          "submit_selector": "button[type='submit']",
          "companies_url": "{base_url.rstrip('/') + '/companies' if base_url else 'https://example.com/companies'}",
          "company_link_selector": "a.company-link",
          "product_link_selector": "a.product-link",
          "product_name_selector": "h1.product-name",
          "lab_name_selector": "div.lab-name",
          "presentation_selector": "div.presentation",
          "price_selector": "div.price",
          "currency_hint": "USD"
        }}
        """
    ).strip()

    selectors_path.write_text(selectors_json, encoding="utf-8")
    print(f"[OK] Created selectors template: {selectors_path}")


def create_sample_html(source: str) -> None:
    samples_dir = PROJECT_ROOT / "src" / "scrapers" / source / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)

    detail_path = samples_dir / "details_sample.html"
    if detail_path.exists():
        print(f"[WARN] Sample HTML already exists: {detail_path}")
    else:
        detail_html = textwrap.dedent(
            f"""
            <!doctype html>
            <html lang=\"en\">
            <head>
                <meta charset=\"utf-8\" />
                <title>{source} product sample</title>
            </head>
            <body>
                <h1 class=\"product-name\">Sample Product</h1>
                <div class=\"lab-name\">Sample Lab</div>
                <div class=\"presentation\">Sample presentation text</div>
                <div class=\"price\">$100.00</div>
            </body>
            </html>
            """
        ).lstrip()
        detail_path.write_text(detail_html, encoding="utf-8")
        print(f"[OK] Created sample HTML: {detail_path}")


def create_dsl_pipeline(source: str) -> None:
    pipelines_dir = PROJECT_ROOT / "dsl" / "pipelines"
    pipelines_dir.mkdir(parents=True, exist_ok=True)

    pipeline_path = pipelines_dir / f"{source}.yaml"
    if pipeline_path.exists():
        print(f"[WARN] DSL pipeline already exists: {pipeline_path}")
        return

    yaml = f"""
    pipeline:
      name: {source}
      description: {source} scraper pipeline compiled through the DSL.
      steps:
        - id: run_pipeline
          component: {source}.pipeline
          params:
            env: null
    """

    pipeline_path.write_text(textwrap.dedent(yaml).lstrip(), encoding="utf-8")
    print(f"[OK] Created DSL pipeline: {pipeline_path}")


def create_plugin_file(source: str) -> None:
    """
    Create src/scrapers/{source}/plugin.py which registers the components
    into the DSL component registry (dsl/components.yaml refers to it).
    """
    scraper_dir = PROJECT_ROOT / "src" / "scrapers" / source
    scraper_dir.mkdir(parents=True, exist_ok=True)

    plugin_path = scraper_dir / "plugin.py"
    if plugin_path.exists():
        print(f"[WARN] Plugin file already exists: {plugin_path}")
        return

    plugin_code = textwrap.dedent(
        f'''"""DSL plugin definitions for the {source} scraper."""

COMPONENT_NAMESPACE = "{source}"

COMPONENTS = {{
    f"{{COMPONENT_NAMESPACE}}.pipeline": {{
        "module": "src.scrapers.{source}.pipeline",
        "callable": "run_{source}",
        "type": "pipeline",
        "description": "Full {source} end-to-end pipeline.",
    }},
    f"{{COMPONENT_NAMESPACE}}.product_detail": {{
        "module": "src.scrapers.{source}.pipeline",
        "callable": "extract_item",
        "type": "scraper",
        "description": "Stub detail extractor for {source}.",
    }},
}}
'''
    ).lstrip()

    plugin_path.write_text(plugin_code, encoding="utf-8")
    print(f"[OK] Created DSL plugin: {plugin_path}")


def create_airflow_dag(source: str) -> None:
    dags_dir = PROJECT_ROOT / "dags"
    dags_dir.mkdir(parents=True, exist_ok=True)

    dag_path = dags_dir / f"scraper_{source}.py"
    if dag_path.exists():
        print(f"[WARN] DAG already exists: {dag_path}")
        return

    dag_code = f"""
    \"\"\"
    Airflow DAG for running the {source} scraper daily.
    \"\"\"

    from datetime import timedelta

    from airflow import DAG
    from airflow.operators.python import PythonOperator
    from airflow.utils.dates import days_ago


    def _run_{source}_pipeline(**context):
        from src.scrapers.{source}.pipeline import run_{source}
        out_path = run_{source}()
        print("[{source} DAG] run completed. Output:", out_path)
        return str(out_path)


    default_args = {{
        "owner": "scraper",
        "depends_on_past": False,
        "email_on_failure": False,
        "email_on_retry": False,
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    }}

    with DAG(
        dag_id="scraper_{source}_daily",
        description="Daily scraper for {source} (v4.8)",
        default_args=default_args,
        schedule_interval="0 3 * * *",  # daily at 03:00
        start_date=datetime(2024, 1, 1),  # Fixed start date instead of days_ago
        catchup=False,
        tags=["scraper", "{source}"],
    ) as dag:

        run_{source}_task = PythonOperator(
            task_id="run_{source}_pipeline",
            python_callable=_run_{source}_pipeline,
            provide_context=True,
        )
    """
    dag_path.write_text(textwrap.dedent(dag_code).lstrip(), encoding="utf-8")
    print(f"[OK] Created Airflow DAG: {dag_path}")


def main():
    parser = argparse.ArgumentParser(description="Scaffold a new scraper (code + config + DAG).")
    parser.add_argument("source", help="New scraper source name, e.g. 'argentina2' or 'canada_quebec'")
    parser.add_argument(
        "--engine",
        choices=["selenium", "playwright", "http"],
        default="selenium",
        help="Scraping engine type (default: selenium)",
    )
    parser.add_argument(
        "--requires-login",
        action="store_true",
        help="Mark this scraper as requiring login (config + code comments).",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive mode: prompt for configuration values.",
    )
    parser.add_argument("--base-url", help="Root URL for the scraper (required unless --interactive)")
    parser.add_argument("--login-url", help="Login URL (only needed if --requires-login)")
    parser.add_argument(
        "--username-prefix",
        help="Environment variable prefix for usernames (default: {SOURCE}_USER_)",
    )
    parser.add_argument(
        "--password-prefix",
        help="Environment variable prefix for passwords (default: {SOURCE}_PASS_)",
    )

    args = parser.parse_args()
    source = args.source.strip()
    
    # Validate source name
    if not source:
        raise SystemExit("Source name cannot be empty.")
    
    if not source.isidentifier():
        raise SystemExit(
            f"Invalid source name '{source}'. Use a valid Python identifier "
            "(letters, numbers, underscores only, no spaces)."
        )
    
    # Check if scraper already exists
    scraper_dir = PROJECT_ROOT / "src" / "scrapers" / source
    if scraper_dir.exists() and (scraper_dir / "pipeline.py").exists():
        response = input(f"Scraper '{source}' already exists. Overwrite? [y/N]: ").strip().lower()
        if response != 'y':
            print("Aborted.")
            return
    
    print(f"[INFO] Creating new scraper: {source}")
    print(f"[INFO] Engine: {args.engine}, requires_login={args.requires_login}")
    
    # Collect configuration
    config = collect_scraper_config(
        source,
        args.engine,
        args.requires_login,
        args.interactive,
        base_url=args.base_url,
        login_url=args.login_url,
        username_prefix=args.username_prefix,
        password_prefix=args.password_prefix,
    )

    # Validate configuration
    if not validate_url(config["base_url"]):
        raise SystemExit(f"Invalid base_url: {config['base_url']}")

    if "example.com" in config["base_url"]:
        raise SystemExit("base_url cannot be left as an example.com placeholder")

    if args.requires_login and not validate_url(config["login_url"]):
        raise SystemExit(f"Invalid login_url: {config['login_url']}")

    try:
        create_scraper_package(source, args.engine, args.requires_login, config)
        create_source_config(source, args.engine, args.requires_login, config)
        create_selectors_template(source, config["base_url"])
        create_sample_html(source)
        create_dsl_pipeline(source)
        create_plugin_file(source)
        create_airflow_dag(source)
        
        print("\n" + "="*60)
        print("[DONE] Scraper scaffolded successfully!")
        print("="*60)
        print(f"\nCreated files:")
        print(f"  ✓ Scraper code:   src/scrapers/{source}/pipeline.py")
        print(f"  ✓ Source config:  config/sources/{source}.yaml")
        print(f"  ✓ Airflow DAG:    dags/scraper_{source}.py")
        print(f"  ✓ DSL pipeline:   dsl/pipelines/{source}.yaml")
        print(f"  ✓ Plugin:          src/scrapers/{source}/plugin.py")
        print(f"  ✓ Selectors:       src/scrapers/{source}/selectors.json")
        print(f"  ✓ Sample HTML:     src/scrapers/{source}/samples/details_sample.html")
        
        print(f"\nNext steps:")
        print(f"  1. Review and customize selectors in src/scrapers/{source}/selectors.json")
        print(f"  2. Test the pipeline: python -m src.scrapers.{source}.pipeline")
        if args.requires_login:
            print(f"  3. Set environment variables:")
            print(f"     - {config['username_env_prefix']}1=your_username")
            print(f"     - {config['password_env_prefix']}1=your_password")
        print(f"  4. Update config/sources/{source}.yaml with any additional settings")
        print(f"  5. Ensure PYTHONPATH in Airflow includes the project root")
        print()
        
    except Exception as exc:
        print(f"\n[ERROR] Failed to create scraper: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
