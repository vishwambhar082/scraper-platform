# file: src/run_tracking/models.py
"""
Dataclasses describing run / step metadata independent of DB schema.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from src.observability.run_trace_context import get_current_tenant_id
from src.scheduler import scheduler_db_adapter as db


@dataclass
class RunRecord:
    run_id: str
    source_name: str
    tenant_id: str = field(default_factory=get_current_tenant_id)
    status: str = "pending"
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    meta: Dict[str, Any] = field(default_factory=dict)
    variant_id: Optional[str] = None
    jira_issue_key: Optional[str] = None
    airflow_dag_id: Optional[str] = None
    airflow_dag_run_id: Optional[str] = None
    run_type: str = "FULL_REFRESH"

    def save(self, conn=None) -> None:
        """Persist the run record inside a transaction."""

        payload_meta = dict(self.meta)
        if self.variant_id:
            payload_meta.setdefault("variant_id", self.variant_id)

        db.upsert_run(
            run_id=self.run_id,
            source=self.source_name,
            tenant_id=self.tenant_id,
            status=self.status,
            started_at=self.started_at,
            finished_at=self.finished_at,
            duration_seconds=None,
            metadata=payload_meta,
            conn=conn,
        )


@dataclass
class StepRecord:
    run_id: str
    step_name: str
    tenant_id: str = field(default_factory=get_current_tenant_id)
    status: str = "pending"
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def save(self, conn=None) -> None:
        """Persist the step record inside a transaction."""

        db.record_run_step(
            step_id=f"{self.run_id}-{self.step_name}-{self.started_at.isoformat()}",
            run_id=self.run_id,
            tenant_id=self.tenant_id,
            name=self.step_name,
            status=self.status,
            started_at=self.started_at,
            duration_seconds=None,
            conn=conn,
        )
