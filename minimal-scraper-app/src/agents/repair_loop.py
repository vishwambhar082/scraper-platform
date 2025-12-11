from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from psycopg2.extras import RealDictCursor

from src.agents.deepagent_repair_engine import run_repair_session
from src.common import db
from src.common.logging_utils import get_logger

log = get_logger("agent-repair-loop")


@dataclass
class AnomalyRecord:
    """Represents an anomaly detected in a run."""

    id: str
    run_id: str
    source: str
    anomaly_type: str
    details: dict


@dataclass
class PatchProposal:
    """Represents a proposed patch."""

    diff_preview: str
    confidence: float


class SnapshotReader:
    """Helper to read snapshots and list anomalies for repair."""

    def __init__(self, source: str, tenant_id: Optional[str] = None) -> None:
        self.source = source
        self.tenant_id = tenant_id or "default"

    def _fetch_drift_events(self, run_id: Optional[str], limit: int) -> List[AnomalyRecord]:
        clauses = ["source = %s", "tenant_id = %s", "resolved IS NOT TRUE"]
        params: List[Any] = [self.source, self.tenant_id]
        if run_id:
            clauses.append("run_id = %s")
            params.append(run_id)
        where_clause = " AND ".join(clauses)

        with db.transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT id, run_id, drift_type, details, detected_at
                    FROM scraper.drift_events
                    WHERE {where_clause}
                    ORDER BY detected_at DESC
                    LIMIT %s
                    """,
                    (*params, limit),
                )
                rows = cur.fetchall()

        anomalies: List[AnomalyRecord] = []
        for row in rows:
            details = row.get("details") or {}
            details["detected_at"] = row["detected_at"].isoformat()
            anomalies.append(
                AnomalyRecord(
                    id=str(row["id"]),
                    run_id=row.get("run_id") or "unknown",
                    source=self.source,
                    anomaly_type=row["drift_type"],
                    details=details,
                )
            )
        return anomalies

    def _fetch_qc_failures(self, run_id: Optional[str], limit: int) -> List[AnomalyRecord]:
        clauses = ["source = %s", "tenant_id = %s", "failed_records > 0"]
        params: List[Any] = [self.source, self.tenant_id]
        if run_id:
            clauses.append("run_id = %s")
            params.append(run_id)
        where_clause = " AND ".join(clauses)

        with db.transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT id, run_id, failed_records, total_records, failure_reasons, created_at
                    FROM scraper.data_quality
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (*params, limit),
                )
                rows = cur.fetchall()

        anomalies: List[AnomalyRecord] = []
        for row in rows:
            details = {
                "failed_records": row.get("failed_records", 0),
                "total_records": row.get("total_records", 0),
                "failure_reasons": row.get("failure_reasons") or {},
                "detected_at": row["created_at"].isoformat(),
            }
            anomalies.append(
                AnomalyRecord(
                    id=str(row["id"]),
                    run_id=row["run_id"],
                    source=self.source,
                    anomaly_type="qc_failure",
                    details=details,
                )
            )
        return anomalies

    def list_recent_anomalies(
        self, run_id: Optional[str] = None, limit: int = 10
    ) -> List[AnomalyRecord]:
        """
        Query drift and QC tables to find anomalies requiring repair.
        """
        drift = self._fetch_drift_events(run_id, limit)
        qc = self._fetch_qc_failures(run_id, limit)
        combined = drift + qc
        combined.sort(key=lambda a: a.details.get("detected_at", ""), reverse=True)
        return combined[:limit]


class RepairEngine:
    """Repair engine that uses agent components to propose patches."""

    def __init__(self, source: str, orchestrator=None) -> None:
        self.source = source
        self.orchestrator = orchestrator

    def propose_patch_for_anomaly(self, anomaly: AnomalyRecord) -> Optional[PatchProposal]:
        """
        Propose a patch for a given anomaly.

        Returns None if no patch can be proposed.
        """
        # Delegate to the repair session
        try:
            results = run_repair_session(self.source)
            if results:
                # Convert PatchResult to PatchProposal
                # This is a simplified mapping
                return PatchProposal(
                    diff_preview=f"Patch proposed for {anomaly.anomaly_type}",
                    confidence=0.7,
                )
        except Exception as exc:
            log.warning("Failed to propose patch", extra={"error": str(exc), "anomaly_id": anomaly.id})
        return None


def run_repair_loop(
    source: str,
    run_id: Optional[str] = None,
    max_patches: int = 10,
    tenant_id: Optional[str] = None,
) -> None:
    """
    High-level DeepAgent repair loop:

      1) Load snapshots/anomalies for a source (optionally a specific run_id).
      2) Feed them into RepairEngine via AgentOrchestrator.
      3) Print/emit proposed patches; applying them is a separate step.

    This wires the existing components into a concrete workflow and can
    be called from a CLI tool or Airflow task.
    """
    reader = SnapshotReader(source=source, tenant_id=tenant_id)
    repair_engine = RepairEngine(source=source)

    anomalies = reader.list_recent_anomalies(run_id=run_id, limit=max_patches)
    if not anomalies:
        log.info("No anomalies found for repair", extra={"source": source, "run_id": run_id})
        return

    for idx, anomaly in enumerate(anomalies, start=1):
        log.info(
            "Processing anomaly",
            extra={"source": source, "run_id": anomaly.run_id, "anomaly_id": anomaly.id},
        )
        proposal = repair_engine.propose_patch_for_anomaly(anomaly)
        if not proposal:
            log.info("No patch proposed for anomaly", extra={"anomaly_id": anomaly.id})
            continue

        # For now, just log it; a separate manual/CI step can apply.
        log.info(
            "Patch proposed",
            extra={
                "anomaly_id": anomaly.id,
                "patch_preview": proposal.diff_preview[:1000],
            },
        )

