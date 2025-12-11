# src/audit/audit_log.py
from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Optional
from src.common.logging_utils import get_logger
from src.common.paths import LOGS_DIR
from src.audit.audit_db_writer import write_audit_event_to_db
from src.observability.run_trace_context import get_current_tenant_id

log = get_logger("audit-log")
_AUDIT_FILE: Path = LOGS_DIR / "audit.log"
_LAST_HASH: Optional[str] = None

@dataclass
class AuditEvent:
    ts: str
    actor: str
    action: str
    entity_type: str
    entity_id: str
    metadata: Dict[str, Any]
    prev_hash: Optional[str]
    hash: Optional[str] = None

def _compute_hash(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()

def log_event(
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> AuditEvent:
    global _LAST_HASH
    metadata = metadata or {}
    event = AuditEvent(
        ts=datetime.utcnow().isoformat(timespec="seconds") + "Z",
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata=metadata,
        prev_hash=_LAST_HASH,
    )
    payload = asdict(event)
    payload["hash"] = _compute_hash({**payload, "hash": None})
    event.hash = payload["hash"]

    # Write to file log (always)
    _AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _AUDIT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, sort_keys=True) + "\n")
    _LAST_HASH = event.hash

    # Write to database (durable storage for compliance)
    # Transform payload to match DB schema: event_type, source, run_id, tenant_id, payload
    db_payload = {
        "event_type": action,  # Use action as event_type
        "source": metadata.get("source") or "",
        "run_id": metadata.get("run_id") or "",
        "tenant_id": metadata.get("tenant_id") or get_current_tenant_id() or "default",
        **payload,  # Include full payload
    }
    try:
        write_audit_event_to_db(db_payload)
    except Exception as e:
        log.warning("Failed to write audit event to DB (file log succeeded): %s", e)

    log.debug("Audit event written: %s %s %s", action, entity_type, entity_id)
    return event
