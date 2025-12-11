"""Startup-time validation helpers."""

from __future__ import annotations

import logging
import os
from typing import List

from src.api.constants import EXTRA_REQUIRED_ENV_VARS_ENV
from src.db.schema_version import (
    get_schema_version,
    schema_version_table_exists,
    set_schema_version,
)

log = logging.getLogger(__name__)

REQUIRED_ENV_VARS = ("DB_URL", "SCRAPER_SECRET_KEY")


def _additional_required_env_vars() -> List[str]:
    """Parse any extra required env vars configured via ``EXTRA_REQUIRED_ENV_VARS``."""

    raw = os.getenv(EXTRA_REQUIRED_ENV_VARS_ENV, "")
    return [part.strip() for part in raw.split(",") if part.strip()]


def get_required_env_vars() -> List[str]:
    """Return the full list of env vars that must be present."""

    combined = list(REQUIRED_ENV_VARS) + _additional_required_env_vars()
    # Preserve order but de-dupe
    deduped: list[str] = []
    for key in combined:
        if key not in deduped:
            deduped.append(key)
    return deduped


def missing_required_env_vars() -> List[str]:
    """Return any required env vars that are not set or are empty."""

    return [key for key in get_required_env_vars() if not os.getenv(key)]


def validate_required_env_vars() -> None:
    """Validate that all required environment variables are present."""

    missing = missing_required_env_vars()
    if missing:
        log.error("Missing required environment variables", extra={"missing_env": missing})
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")


def validate_schema_version(expected_version: int) -> int:
    """Validate the schema version matches ``expected_version``."""

    if not schema_version_table_exists():
        log.error(
            "DB schema version table missing; ensure migrations are applied",
            extra={"expected": expected_version},
        )
        raise RuntimeError("Database schema_version table missing; apply migrations before starting")

    ver = get_schema_version()
    if ver is None:
        log.info(
            "Initializing empty DB schema version row",
            extra={"expected": expected_version},
        )
        set_schema_version(expected_version)
        return expected_version
    if ver != expected_version:
        log.error(
            "DB schema mismatch",
            extra={"expected": expected_version, "found": ver},
        )
        raise RuntimeError(
            f"DB schema version {ver if ver is not None else 'unknown'} does not match expected {expected_version}"
        )
    return ver
