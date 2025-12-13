# src/processors/pcid_matcher.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from src.common.types import NormalizedRecord, PCIDMatchResult, RawRecord
from src.governance.openfeature import is_enabled
from src.processors.vector_store import (
    BasePCIDVectorBackend,
    PCIDVectorStore,
    connect_vector_store_backend,
    embed_pcid_record,
)


def _normalize_field(value: Optional[str]) -> str:
    """Normalize a string value for consistent PCID matching keys."""

    return (value or "").strip().lower()


def _coerce_normalized_record(record: NormalizedRecord | RawRecord | Mapping[str, Any]) -> NormalizedRecord:
    """Convert mappings into ``NormalizedRecord`` instances for typing safety."""

    if isinstance(record, NormalizedRecord):
        return record
    if isinstance(record, RawRecord):
        payload = record.model_dump()
    elif isinstance(record, Mapping):
        payload = dict(record)
    else:  # pragma: no cover - defensive type guard
        raise TypeError(f"Unsupported record type for normalization: {type(record)!r}")
    return NormalizedRecord.model_validate(payload)


def _make_key(record: NormalizedRecord | RawRecord | Mapping[str, Any]) -> Tuple[str, str, str]:
    """Build a normalized match key from a unified record."""

    normalized = _coerce_normalized_record(record)
    name = _normalize_field(normalized.name)
    company = _normalize_field(normalized.company)
    currency = _normalize_field(normalized.currency)
    return name, company, currency


def load_pcid_master(path: Path) -> List[RawRecord]:
    """Load PCID master records from a JSONL or JSON array file.

    Missing files return an empty list to keep local pipelines ergonomic.

    Args:
        path: Path pointing to a JSON or JSONL file.

    Returns:
        List of ``RawRecord`` entries parsed from the file.
    """

    if not path.exists():
        return []

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return []

    # Accept both JSONL and JSON array payloads.
    if content.lstrip().startswith("["):
        data = json.loads(content)
        if isinstance(data, list):
            return [RawRecord.model_validate(item) for item in data if isinstance(item, dict)]
        return []

    records: List[RawRecord] = []
    for line in content.splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            records.append(RawRecord.model_validate(parsed))
    return records


def build_pcid_index(
    records: Iterable[NormalizedRecord | RawRecord | Mapping[str, Any]]
) -> Dict[Tuple[str, str, str], str]:
    """Create an exact-match lookup index keyed by normalized fields."""

    index: Dict[Tuple[str, str, str], str] = {}
    for record in records:
        normalized = _coerce_normalized_record(record)
        pcid = getattr(normalized, "pcid", None)
        if not pcid:
            continue
        index[_make_key(normalized)] = str(pcid)
    return index


def build_vector_store(records: Iterable[Mapping[str, Any]], dims: int = 48) -> PCIDVectorStore:
    """Populate a :class:`PCIDVectorStore` from master records."""

    store = PCIDVectorStore(dims=dims)
    store.populate_from_records(records)
    return store


def persist_pcid_mappings(mappings: Iterable[PCIDMatchResult | Mapping[str, Any]], path: Path) -> None:
    """Write PCID mapping decisions to JSONL for downstream auditing."""

    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for mapping in mappings:
        if isinstance(mapping, PCIDMatchResult):
            payload = mapping.model_dump()
        else:
            payload = dict(mapping)
        lines.append(json.dumps(payload))
    path.write_text("\n".join(lines), encoding="utf-8")


def match_pcid_with_confidence(
    unified_record: NormalizedRecord | RawRecord | Mapping[str, Any],
    pcid_index: Mapping[Tuple[str, str, str], str],
    *,
    vector_store: Optional[BasePCIDVectorBackend] = None,
    min_similarity: float = 0.8,
) -> Tuple[Optional[str], float]:
    """Match a unified record against the PCID index with optional similarity fallback."""

    normalized = _coerce_normalized_record(unified_record)
    normalized_payload = (
        normalized if isinstance(normalized, Mapping) else normalized.model_dump()
    )
    payload_for_backend = (
        dict(unified_record)
        if isinstance(unified_record, Mapping)
        else (normalized_payload if isinstance(normalized_payload, Mapping) else {})
    )
    key = _make_key(normalized)
    exact = pcid_index.get(key)
    if exact:
        return exact, 1.0

    if not is_enabled("pcid.vector_store.similarity_fallback", default=True):
        return None, 0.0

    backend: Optional[BasePCIDVectorBackend] = vector_store
    if backend is None and is_enabled("pcid.vector_store.remote_backend", default=True):
        backend = connect_vector_store_backend()

    if backend is None:
        return None, 0.0

    if hasattr(backend, "query_record"):
        matches = backend.query_record(
            payload_for_backend, top_k=1, threshold=min_similarity  # type: ignore[arg-type]
        )
    else:
        dims = getattr(backend, "dims", 48)
        query_vec = embed_pcid_record(normalized_payload, dims=dims)
        matches = backend.query(query_vec, top_k=1, threshold=min_similarity)

    if not matches:
        return None, 0.0

    best = matches[0]
    pcid = best.get("pcid") if isinstance(best, Mapping) else None
    score = float(best.get("score", 0.0)) if isinstance(best, Mapping) else 0.0
    if not pcid:
        return None, score
    if score <= 0:
        return None, 0.0
    return pcid, score


def match_pcid(
    unified_record: NormalizedRecord | RawRecord | Mapping[str, Any],
    pcid_index: Mapping[Tuple[str, str, str], str],
    *,
    vector_store: Optional[BasePCIDVectorBackend] = None,
    min_similarity: float = 0.8,
) -> Optional[str]:
    """Compatibility wrapper that returns only the PCID string."""

    pcid, _ = match_pcid_with_confidence(
        unified_record,
        pcid_index,
        vector_store=vector_store,
        min_similarity=min_similarity,
    )
    return pcid


def match_records(
    records: Iterable[NormalizedRecord | RawRecord | Mapping[str, Any]],
    pcid_index: Mapping[Tuple[str, str, str], str],
    *,
    vector_store: Optional[BasePCIDVectorBackend] = None,
    min_similarity: float = 0.8,
) -> List[PCIDMatchResult]:
    """Match an iterable of unified records and return PCID decisions.

    The helper is designed for pipeline integration and plugin discovery,
    returning structured :class:`PCIDMatchResult` objects. It intentionally
    leaves side effects to callers so it can be used safely in both
    synchronous and async contexts.
    """

    results: List[PCIDMatchResult] = []
    for record in records:
        normalized = _coerce_normalized_record(record)
        pcid, confidence = match_pcid_with_confidence(
            normalized,
            pcid_index,
            vector_store=vector_store,
            min_similarity=min_similarity,
        )
        results.append(
            PCIDMatchResult(
                record=normalized,
                pcid=pcid,
                confidence=confidence,
                method="exact" if confidence >= 1.0 else "vector" if pcid else "none",
            )
        )
    return results

