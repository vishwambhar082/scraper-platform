from fastapi import APIRouter, Response, status

from src.api import startup_checks
from src.api.constants import EXPECTED_SCHEMA_VERSION

router = APIRouter()


@router.get("/health")
@router.get("/api/health")
def health():
    """
    Basic health check endpoint (backward compatibility).
    Use /health/live or /health/ready for Kubernetes/production.
    """
    return {"status": "ok"}


@router.get("/health/live")
def liveness():
    """
    Liveness probe for Kubernetes/Docker orchestration.

    Returns 200 OK if the application process is running.
    Does NOT check dependencies (DB, external services).

    Kubernetes should restart the pod if this fails.
    """
    return {"status": "ok", "probe": "liveness"}


@router.get("/health/ready")
def readiness(response: Response):
    """
    Readiness probe for Kubernetes/Docker orchestration.

    Returns 200 OK if the application is ready to serve traffic.
    Checks all critical dependencies: database, required env vars.

    Kubernetes should remove pod from load balancer if this fails.
    """
    checks = {
        "database": "unknown",
        "secrets": "unknown"
    }
    ready = True

    # Check database connectivity
    try:
        ver = startup_checks.validate_schema_version(EXPECTED_SCHEMA_VERSION)
        checks["database"] = "ok"
        checks["schema_version"] = ver
    except Exception as exc:
        checks["database"] = f"error: {str(exc)}"
        ready = False

    # Check required environment variables
    missing = startup_checks.missing_required_env_vars()
    if missing:
        checks["secrets"] = f"error: missing {', '.join(missing)}"
        ready = False
    else:
        checks["secrets"] = "ok"

    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "probe": "readiness", "checks": checks}

    return {"status": "ready", "probe": "readiness", "checks": checks}


@router.get("/health/db")
def db_health():
    """
    Database health check (legacy endpoint).
    Verify DB connectivity and schema version.
    """
    try:
        ver = startup_checks.validate_schema_version(EXPECTED_SCHEMA_VERSION)
        return {"status": "ok", "schema_version": ver}
    except Exception as exc:  # pragma: no cover - defensive catch for readiness probes
        return {"status": "error", "error": str(exc)}


@router.get("/health/secrets")
def secrets_health():
    """
    Secrets health check (legacy endpoint).
    Validate required secrets are reachable without returning their values.
    """
    missing = startup_checks.missing_required_env_vars()
    if missing:
        return {"status": "error", "missing": missing}
    return {"status": "ok"}
