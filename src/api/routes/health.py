from fastapi import APIRouter

from src.api import startup_checks
from src.api.constants import EXPECTED_SCHEMA_VERSION

router = APIRouter()


@router.get("/health")
@router.get("/api/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@router.get("/health/db")
def db_health():
    """Verify DB connectivity and schema version."""

    try:
        ver = startup_checks.validate_schema_version(EXPECTED_SCHEMA_VERSION)
        return {"status": "ok", "schema_version": ver}
    except Exception as exc:  # pragma: no cover - defensive catch for readiness probes
        return {"status": "error", "error": str(exc)}


@router.get("/health/secrets")
def secrets_health():
    """Validate required secrets are reachable without returning their values."""

    missing = startup_checks.missing_required_env_vars()
    if missing:
        return {"status": "error", "missing": missing}
    return {"status": "ok"}
