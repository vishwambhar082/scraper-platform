import csv
import json
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from selenium.common.exceptions import NoSuchElementException

from src.common.config_loader import load_config, load_source_config
from src.common.logging_utils import get_logger, sanitize_for_log, safe_log
from src.common.paths import OUTPUT_DIR
from src.agents.agent_orchestrator import orchestrate_source_repair, load_recent_output_counts
from src.engines.selenium_engine import open_with_session
from src.observability import metrics
from src.observability.cost_tracking import record_run_cost
from src.observability.run_trace_context import get_current_run_id, start_run_context
from src.run_tracking import recorder as run_recorder
from src.processors.exporters import database_loader, gcs_exporter, s3_exporter
from src.processors.qc_rules import is_valid
from src.processors.dedupe import dedupe_records
from src.processors.pcid_matcher import (
    build_pcid_index,
    build_vector_store,
    load_pcid_master,
    match_pcid_with_confidence,
    persist_pcid_mappings,
)
from src.processors.vector_store import BasePCIDVectorBackend, get_pcid_backend
from src.processors.unify_fields import unify_record
from src.resource_manager import ResourceManager, get_default_resource_manager
from src.scrapers.alfabeta.alfabeta_full_impl import extract_product
from src.scrapers.alfabeta.company_index import fetch_company_urls
from src.scrapers.alfabeta.product_index import fetch_product_urls
from src.sessions.session_manager import create_session_record
from src.versioning.version_manager import (
    attach_version_metadata,
    build_version_info,
    register_version,
)

log = get_logger("alfabeta-pipeline")

DEFAULT_COMPANIES_URL = "https://example.com/companies"


@dataclass
class PipelineContext:
    source: str
    platform_config: Mapping[str, Any]
    source_config: Dict[str, Any]
    selectors: Dict[str, str]
    run_id: str
    version_info: Dict[str, Any]
    driver: Any
    base_url: str
    pcid_index: Dict[Tuple[str, str, str], str]
    pcid_vector_store: Optional[BasePCIDVectorBackend]
    pcid_min_similarity: float
    baseline_rows: int
    run_started_at: datetime
    env: Optional[str] = None
    variant_id: Optional[str] = None
    invalid_records: int = 0
    output_dir: Path = field(default_factory=lambda: OUTPUT_DIR)


def _resolve_pcid_master_path() -> Path:
    configured = os.getenv("PCID_MASTER_PATH")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[3] / "config" / "pcid_master.jsonl"


def _prepare_pcid_resources(
    platform_config: Mapping[str, Any]
) -> Tuple[Dict[Tuple[str, str, str], str], Optional[BasePCIDVectorBackend]]:
    pcid_master_path = _resolve_pcid_master_path()
    master_records = load_pcid_master(pcid_master_path)
    if not master_records:
        log.info(
            "PCID master missing or empty; skipping similarity index build",
            extra={"path": str(pcid_master_path)},
        )
        return {}, get_pcid_backend(platform_config)

    hash_cfg = platform_config.get("pcid", {}).get("hash", {}) if isinstance(platform_config, Mapping) else {}
    dims = int(hash_cfg.get("dims", 48)) if isinstance(hash_cfg, Mapping) else 48

    pcid_index = build_pcid_index(master_records)
    vector_store = build_vector_store(master_records, dims=dims)
    backend = get_pcid_backend(platform_config, vector_store=vector_store)
    log.info(
        "Loaded PCID master",
        extra={"rows": len(master_records), "index_keys": len(pcid_index), "path": str(pcid_master_path)},
    )
    return pcid_index, backend


def _load_selectors() -> Dict[str, str]:
    selectors_path = Path(__file__).with_name("selectors.json")
    if not selectors_path.exists():
        return {}
    return json.loads(selectors_path.read_text(encoding="utf-8"))


def _is_logged_in(driver, logged_in_selector: Optional[str]) -> bool:
    """Check whether the logged-in indicator is present on the current page."""

    if not logged_in_selector or not hasattr(driver, "find_elements"):
        return False

    try:
        elements = driver.find_elements("css selector", logged_in_selector)
        return bool(elements)
    except NoSuchElementException:
        return False
    except Exception as exc:  # pragma: no cover - defensive guard
        log.debug("Login check failed: %s", exc)
        return False


def ensure_logged_in(
    driver,
    selectors: Dict[str, str],
    source_config: Dict[str, object],
    account_username: Optional[str] = None,
    account_password: Optional[str] = None,
) -> None:
    """Perform a login flow using selectors when enabled and configured."""

    login_cfg = source_config.get("login", {}) if isinstance(source_config, dict) else {}
    if not login_cfg or not login_cfg.get("enabled"):
        log.info("Login disabled for AlfaBeta; continuing without auth")
        return

    login_url = selectors.get("login_url") or login_cfg.get("url") or DEFAULT_COMPANIES_URL
    username_sel = selectors.get("username_selector") or login_cfg.get("username_selector")
    password_sel = selectors.get("password_selector") or login_cfg.get("password_selector")
    submit_sel = selectors.get("submit_selector") or login_cfg.get("submit_selector")
    logged_in_sel = selectors.get("logged_in_check_selector") or login_cfg.get("logged_in_check_selector")
    username = account_username or login_cfg.get("username") or None
    password = account_password or login_cfg.get("password") or None

    if login_cfg.get("username_env"):
        username = username or os.getenv(login_cfg["username_env"], "")
    if login_cfg.get("password_env"):
        password = password or os.getenv(login_cfg["password_env"], "")

    if not all([login_url, username_sel, password_sel, submit_sel]):
        log.warning("Login enabled but selectors or URL are incomplete; skipping login")
        return

    safe_log(
        log,
        "info",
        "Attempting login flow",
        extra=sanitize_for_log({"login_url": login_url}),
    )

    try:
        driver.get(login_url)
        if _is_logged_in(driver, logged_in_sel):
            log.info("Existing AlfaBeta session detected; skipping login form submission")
            return

        if hasattr(driver, "find_element"):
            user_el = driver.find_element("css selector", username_sel)
            pwd_el = driver.find_element("css selector", password_sel)
            submit_el = driver.find_element("css selector", submit_sel)
            if username:
                user_el.send_keys(username)
            if password:
                pwd_el.send_keys(password)
            submit_el.click()

            if logged_in_sel:
                _ = _is_logged_in(driver, logged_in_sel)
        else:
            log.info("Driver does not support form interactions; assuming fake-driver login")
    except NoSuchElementException:
        log.warning("Login selectors not found on page; continuing without login")
    except Exception as exc:  # pragma: no cover - defensive guard
        log.warning("Login attempt failed: %s", exc)


def fetch_listings(ctx: PipelineContext) -> List[str]:
    """Discover company listing URLs."""

    driver = ctx.driver
    driver.get(ctx.base_url)
    companies = fetch_company_urls(driver, ctx.base_url, ctx.selectors, run_id=ctx.run_id)
    run_recorder.record_step(
        ctx.run_id,
        name="company_index",
        status="success",
    )
    return companies


def fetch_details(ctx: PipelineContext, listings: List[str]) -> List[str]:
    """Expand company listings into product detail URLs."""

    driver = ctx.driver
    product_urls: List[str] = []
    for company_url in listings:
        driver.get(company_url)
        product_urls.extend(
            fetch_product_urls(driver, company_url, ctx.selectors, run_id=ctx.run_id)
        )

    run_recorder.record_step(ctx.run_id, name="product_index", status="success")
    return product_urls


def parse_raw(ctx: PipelineContext, details: List[str]) -> List[Dict[str, Any]]:
    """Extract raw product payloads from detail pages."""

    driver = ctx.driver
    raw_records: List[Dict[str, Any]] = []
    for detail_url in details:
        driver.get(detail_url)
        raw_records.append(extract_product(driver, detail_url, ctx.selectors, ctx.run_id))

    run_recorder.record_step(ctx.run_id, name="extract_product", status="success")
    return raw_records


def normalize_records(ctx: PipelineContext, parsed: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Unify raw records and attach metadata."""

    normalized: List[Dict[str, Any]] = []
    for record in parsed:
        unified = unify_record(record)
        enriched = attach_version_metadata(unified, ctx.version_info)
        enriched["run_id"] = ctx.run_id
        normalized.append(enriched)

    return normalized


def match_pcid(ctx: PipelineContext, normalized: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Augment normalized records with PCID matches when available."""

    matched_records: List[Dict[str, Any]] = []
    for record in normalized:
        pcid, confidence = match_pcid_with_confidence(
            record,
            ctx.pcid_index,
            vector_store=ctx.pcid_vector_store,
            min_similarity=ctx.pcid_min_similarity,
        )
        if pcid:
            record["pcid"] = pcid
            record["pcid_confidence"] = confidence
        matched_records.append(record)

    return matched_records


def run_qc(ctx: PipelineContext, matched: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter invalid records and de-duplicate."""

    valid_records: List[Dict[str, Any]] = []
    invalid_count = 0
    for record in matched:
        if is_valid(record):
            metrics.incr("scraper.records_valid", source=ctx.source)
            valid_records.append(record)
        else:
            metrics.incr("scraper.records_invalid", source=ctx.source)
            invalid_count += 1

    deduped = dedupe_records(valid_records) if valid_records else []
    dropped = len(valid_records) - len(deduped)
    if dropped:
        metrics.incr("scraper.records_duplicate", amount=dropped, source=ctx.source)

    ctx.invalid_records = invalid_count
    return deduped


def export_records(ctx: PipelineContext, final: List[Dict[str, Any]]) -> Path:
    """Persist output artifacts and run bookkeeping."""

    export_cfg = ctx.platform_config.get("export", {}) if isinstance(ctx.platform_config, Mapping) else {}
    backends = export_cfg.get("backends") or ["csv"]
    backends = [backend.lower() for backend in backends]

    daily_dir = ctx.output_dir / ctx.source / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
    filename = f"alfabeta_labs_{date.today().isoformat()}.csv"
    out_path = daily_dir / filename

    pcid_mappings: List[Dict[str, Any]] = [
        {
            "product_url": rec.get("product_url"),
            "pcid": rec.get("pcid"),
            "confidence": rec.get("pcid_confidence", 0.0),
            "source": ctx.source,
            "run_id": ctx.run_id,
        }
        for rec in final
        if rec.get("pcid")
    ]

    if final:
        if "csv" in backends:
            with out_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "product_url",
                        "name",
                        "price",
                        "currency",
                        "company",
                        "source",
                        "pcid",
                        "pcid_confidence",
                        "run_id",
                        "_version",
                    ],
                )
                writer.writeheader()
                writer.writerows(final)
            log.info("Wrote %d records to %s", len(final), out_path)
        else:
            log.info("CSV backend disabled; skipping local write")

        validation_rate = len(final) / max(len(final) + ctx.invalid_records, 1)
        if ctx.baseline_rows:
            orchestrate_source_repair(
                source=ctx.source,
                baseline_rows=ctx.baseline_rows,
                current_rows=len(final),
                validation_rate=validation_rate,
                selectors_path=Path(__file__).with_name("selectors.json"),
            )

        if pcid_mappings:
            pcid_mapping_dir = ctx.output_dir / ctx.source / "pcid_mappings"
            mapping_path = pcid_mapping_dir / f"{ctx.source}_pcid_{date.today().isoformat()}.jsonl"
            persist_pcid_mappings(pcid_mappings, mapping_path)
            log.info("Persisted %d PCID mappings to %s", len(pcid_mappings), mapping_path)
    else:
        log.warning("No valid records to write for AlfaBeta run.")

    for backend in backends:
        if backend == "csv":
            continue
        if backend == "db":
            database_loader.export_records(final)
            log.info("Exported %d records to DB backend", len(final))
        elif backend == "s3":
            s3_cfg = export_cfg.get("s3", {}) if isinstance(export_cfg, Mapping) else {}
            bucket = s3_cfg.get("bucket") if isinstance(s3_cfg, Mapping) else None
            prefix = s3_cfg.get("prefix") if isinstance(s3_cfg, Mapping) else None
            if not bucket:
                log.warning("S3 backend configured without a bucket; skipping upload")
                continue
            key = s3_exporter.export_to_s3(final, bucket=bucket, prefix=prefix, object_name=filename)
            log.info("Uploaded %d records to s3://%s/%s", len(final), bucket, key)
        elif backend == "gcs":
            gcs_cfg = export_cfg.get("gcs", {}) if isinstance(export_cfg, Mapping) else {}
            bucket = gcs_cfg.get("bucket") if isinstance(gcs_cfg, Mapping) else None
            prefix = gcs_cfg.get("prefix") if isinstance(gcs_cfg, Mapping) else None
            if not bucket:
                log.warning("GCS backend configured without a bucket; skipping upload")
                continue
            key = gcs_exporter.export_to_gcs(final, bucket=bucket, prefix=prefix, object_name=filename)
            log.info("Uploaded %d records to gs://%s/%s", len(final), bucket, key)
        else:
            log.warning("Unknown export backend '%s'; skipping", backend)

    record_run_cost(
        source=ctx.source,
        run_id=ctx.run_id,
        proxy_cost_usd=0.0,
        compute_cost_usd=0.0,
        other_cost_usd=0.0,
    )

    run_recorder.finish_run(
        ctx.run_id,
        source=ctx.source,
        status="success",
        stats={
            "records": len(final),
            "invalid": ctx.invalid_records,
        },
        metadata={"output_path": str(out_path)},
        variant_id=ctx.variant_id,
        started_at=ctx.run_started_at,
    )
    log.info("Wrote %d records to %s", len(final), out_path)
    return out_path


def run_alfabeta(
    env: Optional[str] = None, variant_id: Optional[str] = None, resource_manager: Optional[ResourceManager] = None
) -> Path:
    """End-to-end pipeline for AlfaBeta.

    The flow stitches together config loading, account/proxy routing, session
    management, engine execution, processors, observability, and versioning to
    mirror the v4.9 dependency model.
    """
    source = "alfabeta"
    log.info("Starting AlfaBeta pipeline run")

    platform_config = load_config(env)
    source_config = load_source_config(source)
    selectors = _load_selectors()
    base_url = source_config.get("base_url") or selectors.get("companies_url") or DEFAULT_COMPANIES_URL
    active_env = platform_config.get("app", {}).get("environment")
    log.info("Pipeline environment resolved to '%s'", active_env)

    _ = start_run_context()
    run_id = get_current_run_id() or date.today().isoformat()
    log.info("Run context initialized", extra={"run_id": run_id})
    run_started_at = datetime.utcnow()
    run_recorder.start_run(run_id, source, metadata={"env": env or "prod"}, variant_id=variant_id)
    version_info = build_version_info(
        scraper=source,
        scraper_version=source_config.get("version"),
        schema_version=source_config.get("schema_version"),
        selectors_version=source_config.get("selectors_version"),
    )
    register_version(
        source=source,
        run_id=run_id,
        version=version_info,
        schema_name=source_config.get("schema_name", "product_record"),
        selectors_payload=selectors,
    )

    active_resource_manager = get_default_resource_manager()

    # 1) ACCOUNT + PROXY
    account_key, username, password = active_resource_manager.account_router.acquire_account(source)
    proxy = active_resource_manager.proxy_pool.choose_proxy(source) or ""
    account_id = account_key.split(":", 1)[1]
    session_record = create_session_record(source, account_id, proxy)

    browser_session = open_with_session(base_url, session_record)
    driver = browser_session.driver

    pcid_index, pcid_vector_store = _prepare_pcid_resources(platform_config)
    baseline_counts = load_recent_output_counts(source)
    baseline_rows = baseline_counts[1] if len(baseline_counts) > 1 else baseline_counts[0] if baseline_counts else 0
    try:
        pcid_min_similarity = float(os.getenv("PCID_MIN_SIMILARITY", "0.8"))
    except ValueError:
        pcid_min_similarity = 0.8

    ctx = PipelineContext(
        source=source,
        platform_config=platform_config,
        source_config=source_config,
        selectors=selectors,
        run_id=run_id,
        version_info=version_info,
        driver=driver,
        base_url=base_url,
        pcid_index=pcid_index,
        pcid_vector_store=pcid_vector_store,
        pcid_min_similarity=pcid_min_similarity,
        baseline_rows=baseline_rows,
        run_started_at=run_started_at,
        env=env,
        variant_id=variant_id,
    )

    try:
        ensure_logged_in(
            driver,
            selectors,
            source_config,
            account_username=username,
            account_password=password,
        )

        listings = fetch_listings(ctx)
        details = fetch_details(ctx, listings)
        parsed = parse_raw(ctx, details)
        normalized = normalize_records(ctx, parsed)
        matched = match_pcid(ctx, normalized)
        qc_passed = run_qc(ctx, matched)
        out_path = export_records(ctx, qc_passed)
        return out_path
    except Exception as exc:
        run_recorder.finish_run(
            run_id,
            source=source,
            status="failed",
            metadata={"error": str(exc)},
            variant_id=variant_id,
            started_at=run_started_at,
        )
        raise
    finally:
        browser_session.quit()
        active_resource_manager.account_router.release_account(account_key)


def main():
    """CLI entry point."""
    out_path = run_alfabeta()
    log.info("Completed AlfaBeta run. Output: %s", out_path)


if __name__ == "__main__":
    main()
