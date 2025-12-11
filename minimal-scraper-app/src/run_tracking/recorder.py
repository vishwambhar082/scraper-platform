from __future__ import annotations

from datetime import datetime
import uuid
from typing import Dict, Optional
import os

from src.common.logging_utils import get_logger
from src.scheduler import scheduler_db_adapter as db
from src.run_tracking.db_session import get_session

log = get_logger("run-tracking")


def _is_db_enabled() -> bool:
    """Return True when database-backed run tracking should be used."""

    return os.getenv("SCRAPER_PLATFORM_DISABLE_DB") != "1"


def _prepare_metadata(metadata: Optional[Dict[str, object]], variant_id: Optional[str]) -> Optional[Dict[str, object]]:
    prepared = dict(metadata or {})
    if variant_id:
        prepared.setdefault("variant_id", variant_id)
    return prepared or None


def start_run(
    run_id: str,
    source: str,
    metadata: Optional[Dict[str, object]] = None,
    *,
    variant_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> str:
    """Record the beginning of a run."""

    if not _is_db_enabled():
        log.debug("DB disabled; skipping run start persist", extra={"run_id": run_id, "source": source})
        return run_id

    started_at = datetime.utcnow()
    with get_session() as session:
        db.upsert_run(
            run_id=run_id,
            source=source,
            tenant_id=tenant_id,
            status="running",
            started_at=started_at,
            metadata=_prepare_metadata(metadata, variant_id),
            conn=session.conn,
        )
    log.info("Recorded run start", extra={"run_id": run_id, "source": source})
    return run_id


def finish_run(
    run_id: str,
    source: str,
    status: str,
    *,
    stats: Optional[Dict[str, object]] = None,
    metadata: Optional[Dict[str, object]] = None,
    variant_id: Optional[str] = None,
    started_at: Optional[datetime] = None,
    tenant_id: Optional[str] = None,
) -> None:
    """Mark a run complete and store summary stats."""

    if not _is_db_enabled():
        log.debug("DB disabled; skipping run finish persist", extra={"run_id": run_id, "source": source})
        return

    finished_at = datetime.utcnow()
    duration_seconds = None
    if started_at:
        duration_seconds = int((finished_at - started_at).total_seconds())

    prepared_metadata = _prepare_metadata(metadata, variant_id)
    if prepared_metadata is None:
        prior_run = db.fetch_run_detail(run_id)
        prepared_metadata = _prepare_metadata(prior_run.metadata if prior_run else None, variant_id)

    with get_session() as session:
        db.upsert_run(
            run_id=run_id,
            source=source,
            tenant_id=tenant_id,
            status=status,
            started_at=started_at or finished_at,
            finished_at=finished_at,
            duration_seconds=duration_seconds,
            stats=stats,
            metadata=prepared_metadata,
            conn=session.conn,
        )
    log.info("Recorded run finish", extra={"run_id": run_id, "status": status})


def record_step(
    run_id: str,
    name: str,
    status: str,
    *,
    started_at: Optional[datetime] = None,
    duration_seconds: Optional[int] = None,
    tenant_id: Optional[str] = None,
) -> str:
    """Store a run step for UI visualization."""

    if not _is_db_enabled():
        log.debug("DB disabled; skipping step persist", extra={"run_id": run_id, "name": name})
        return f"{run_id}-{uuid.uuid4().hex[:8]}"

    started_at = started_at or datetime.utcnow()
    step_id = f"{run_id}-{uuid.uuid4().hex[:8]}"
    with get_session() as session:
        db.record_run_step(
            step_id=step_id,
            run_id=run_id,
            tenant_id=tenant_id,
            name=name,
            status=status,
            started_at=started_at,
            duration_seconds=duration_seconds,
            conn=session.conn,
        )
    return step_id


class RunRecorder:
    """Lightweight helper for recording run lifecycle events."""

    def __init__(self, *, tenant_id: Optional[str] = None) -> None:
        self.tenant_id = tenant_id

    def start_run(
        self,
        run_id: str,
        source: str,
        metadata: Optional[Dict[str, object]] = None,
        *,
        variant_id: Optional[str] = None,
    ) -> str:
        return start_run(
            run_id=run_id,
            source=source,
            metadata=metadata,
            variant_id=variant_id,
            tenant_id=self.tenant_id,
        )

    def finish_run(
        self,
        run_id: str,
        source: str,
        status: str,
        *,
        stats: Optional[Dict[str, object]] = None,
        metadata: Optional[Dict[str, object]] = None,
        variant_id: Optional[str] = None,
        started_at: Optional[datetime] = None,
    ) -> None:
        finish_run(
            run_id=run_id,
            source=source,
            status=status,
            stats=stats,
            metadata=metadata,
            variant_id=variant_id,
            started_at=started_at,
            tenant_id=self.tenant_id,
        )

    def record_step(
        self,
        run_id: str,
        name: str,
        status: str,
        *,
        started_at: Optional[datetime] = None,
        duration_seconds: Optional[int] = None,
    ) -> str:
        return record_step(
            run_id=run_id,
            name=name,
            status=status,
            started_at=started_at,
            duration_seconds=duration_seconds,
            tenant_id=self.tenant_id,
        )
