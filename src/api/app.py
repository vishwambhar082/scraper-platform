import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import startup_checks
from src.api.constants import EXPECTED_SCHEMA_VERSION
from src.api.middleware.tenant_middleware import TenantMiddleware
from src.api.routes import (
    airflow_control,
    airflow_proxy,
    audit,
    costs,
    deploy,
    health,
    integration,
    logs,
    runs,
    sessions,
    source_health,
    steps,
    variants,
)

app = FastAPI(title="Scraper Platform API", version="5.0")

# Enable CORS for the dashboard frontend
# Production: Set CORS_ORIGINS env var to comma-separated list of allowed origins
allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Add tenant middleware for multi-tenant isolation
app.add_middleware(TenantMiddleware)


@app.on_event("startup")
async def verify_startup():
    """Fail fast if critical dependencies are not ready."""

    startup_checks.validate_required_env_vars()
    startup_checks.validate_schema_version(EXPECTED_SCHEMA_VERSION)


app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(runs.router)
app.include_router(steps.router)
app.include_router(source_health.router)
app.include_router(airflow_proxy.router)
app.include_router(airflow_control.router)
app.include_router(variants.router)
app.include_router(costs.router)
app.include_router(audit.router)
app.include_router(integration.router)
app.include_router(logs.router)
app.include_router(deploy.router)
