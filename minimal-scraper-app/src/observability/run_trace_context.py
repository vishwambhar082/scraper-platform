# src/observability/run_trace_context.py
from __future__ import annotations

import contextvars
from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

from src.common.logging_utils import get_logger

log = get_logger("run-trace-context")

_run_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("run_id", default=None)
_tenant_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("tenant_id", default="default")


@dataclass
class RunContext:
    run_id: str
    tenant_id: str


def start_run_context(run_id: Optional[str] = None) -> RunContext:
    rid = run_id or str(uuid4())
    _run_id_var.set(rid)
    tenant_id = get_current_tenant_id()
    log.debug("Run context started: %s (tenant=%s)", rid, tenant_id)
    return RunContext(run_id=rid, tenant_id=tenant_id)


def start_tenant_context(tenant_id: str) -> None:
    tenant = tenant_id or "default"
    _tenant_id_var.set(tenant)
    log.debug("Tenant context set: %s", tenant)


def get_current_run_id() -> Optional[str]:
    return _run_id_var.get()


def get_current_tenant_id() -> str:
    """Return the active tenant id, defaulting to 'default'."""

    return _tenant_id_var.get()
