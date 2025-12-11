from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from src.common.logging_utils import get_logger
from src.common.paths import OUTPUT_DIR
from src.versioning.schema_registry import get_schema, load_default_schemas
from src.versioning.version_policy import VersionPolicy

log = get_logger("version-manager")

PLATFORM_VERSION = "4.9.0"
SNAPSHOT_DIR = OUTPUT_DIR / "version_snapshots"
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class VersionInfo:
    """Version metadata attached to runs, outputs, and records."""

    platform: str
    scraper: str
    scraper_version: Optional[str] = None
    schema_version: Optional[str] = None
    selectors_version: Optional[str] = None
    code_commit: Optional[str] = None

    def as_dict(self) -> Dict[str, Optional[str]]:
        return {
            "platform": self.platform,
            "scraper": self.scraper,
            "scraper_version": self.scraper_version,
            "schema_version": self.schema_version,
            "selectors_version": self.selectors_version,
            "code_commit": self.code_commit,
        }


@dataclass
class SnapshotRecord:
    """Persisted snapshot metadata for a run."""

    source: str
    run_id: str
    schema_name: str
    schema_signature: str
    selectors_signature: str
    path: Path
    version: VersionInfo


def get_platform_version() -> str:
    """Return the platform version, allowing an environment override for CI/packaging."""

    return os.getenv("SCRAPER_PLATFORM_VERSION", PLATFORM_VERSION)


def _hash_payload(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_version_info(
    scraper: str,
    *,
    scraper_version: str | None = None,
    schema_version: str | None = None,
    selectors_version: str | None = None,
    code_commit: str | None = None,
) -> VersionInfo:
    """Construct a VersionInfo with platform + scraper metadata."""

    platform_version = get_platform_version()
    return VersionInfo(
        platform=platform_version,
        scraper=scraper,
        scraper_version=scraper_version,
        schema_version=schema_version,
        selectors_version=selectors_version,
        code_commit=code_commit,
    )


def attach_version_metadata(record: Dict[str, object], version: VersionInfo) -> Dict[str, object]:
    """Return a new record that includes version metadata under `_version`."""

    enriched = dict(record)
    enriched.setdefault("_version", {}).update(version.as_dict())
    return enriched


def _latest_snapshot_path(source: str) -> Path | None:
    source_dir = SNAPSHOT_DIR / source
    if not source_dir.exists():
        return None
    snapshots = sorted(source_dir.glob("*.json"))
    return snapshots[-1] if snapshots else None


def register_version(
    *,
    source: str,
    run_id: str,
    version: VersionInfo,
    schema_name: str,
    selectors_payload: Dict[str, object] | None = None,
    version_policy: VersionPolicy | None = None,
) -> SnapshotRecord:
    """Persist a lightweight snapshot that captures schema + selector signatures.

    This is intentionally filesystem-based to avoid database dependencies while
    still providing reproducibility for downstream tests and audits.
    """

    load_default_schemas()
    policy = version_policy or VersionPolicy()

    schema = get_schema(schema_name)
    if not schema:
        raise ValueError(f"Schema '{schema_name}' is not registered")

    schema_sig = _hash_payload(schema)
    selectors_sig = _hash_payload(selectors_payload or {})

    latest_path = _latest_snapshot_path(source)
    if latest_path and latest_path.exists():
        try:
            latest = json.loads(latest_path.read_text(encoding="utf-8"))
            latest_schema_sig = latest.get("schema_signature")
            if latest_schema_sig and latest_schema_sig != schema_sig:
                log.warning(
                    "Schema signature drift detected for %s: %s -> %s",
                    source,
                    latest_schema_sig,
                    schema_sig,
                )
                if not policy.keep_history:
                    raise ValueError("Schema drift detected while history disabled")
        except ValueError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            log.warning("Failed to read latest snapshot for %s: %s", source, exc)

    source_dir = SNAPSHOT_DIR / source
    source_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    snapshot_path = source_dir / f"{run_id}_{ts}.json"

    payload = {
        "source": source,
        "run_id": run_id,
        "version": version.as_dict(),
        "schema_name": schema_name,
        "schema_signature": schema_sig,
        "selectors_signature": selectors_sig,
        "selectors": selectors_payload or {},
        "created_at": ts,
    }
    snapshot_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    log.info("Registered version snapshot for %s at %s", source, snapshot_path)

    return SnapshotRecord(
        source=source,
        run_id=run_id,
        schema_name=schema_name,
        schema_signature=schema_sig,
        selectors_signature=selectors_sig,
        path=snapshot_path,
        version=version,
    )
