"""Example HTTP pipeline demonstrating engine selection and rate limiting.

This module intentionally avoids any side effects and can be used as a
reference for wiring the HTTP engine with configuration-driven rate limiting.
"""

from __future__ import annotations

from typing import Optional

from src.common.config_loader import load_settings, load_source_config
from src.engines import (
    build_rate_limiter_from_config,
    get_engine_type_for_source,
    get_http_engine,
)


DEFAULT_SOURCE = "template"


def run_sample_http_pipeline(source_name: str = DEFAULT_SOURCE, url_override: Optional[str] = None) -> str:
    """Run a minimal HTTP pipeline for demonstration purposes.

    This function loads the requested source configuration, validates the engine
    choice, builds a rate limiter from global settings, and executes a single
    HTTP request using the configured base URL (or an explicit override).
    """

    # 1. Load global + source config
    settings = load_settings()
    source_cfg = load_source_config(source_name)

    # 2. Decide engine type (for sanity)
    engine_type = get_engine_type_for_source(source_cfg)
    if engine_type != "http":
        raise RuntimeError(
            f"{source_name} must be configured with engine.type=http, got {engine_type!r}"
        )

    # 3. Build rate limiter from global config
    rate_limiter = build_rate_limiter_from_config(settings)

    # 4. Get HTTP engine primitives
    send_request, HttpRequestConfig = get_http_engine()

    # 5. Use it
    url = url_override or source_cfg.get("base_url")
    if not url:
        raise ValueError(
            f"Source config for {source_name} is missing 'base_url'; "
            "provide url_override to run the sample"
        )

    req_cfg = HttpRequestConfig(
        url=url,
        timeout=30.0,
        max_retries=3,
        backoff_seconds=1.0,
        proxy=None,
    )

    result = send_request(req_cfg, rate_limiter=rate_limiter)
    return result.text


__all__ = ["run_sample_http_pipeline"]
