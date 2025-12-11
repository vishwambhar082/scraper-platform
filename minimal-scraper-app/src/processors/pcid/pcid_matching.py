"""
PCID matching utilities.

Goal:
    - Take a normalized pharma record
    - Build a text query describing the product
    - Ask a VectorStore / PCID index for nearest candidates
    - Return the best PCID match (if any) with score + method

This module is written to:
    - Work against ANY vector store implementation that exposes a simple
      `search(text, top_k)` API returning (pcid, score).
    - Never crash the pipeline on matching failures – it fails soft.

Typical flow:

    from src.processors.pcid.pcid_matching import match_pcid_batch
    from src.processors.pcid.vector_store import PcidVectorStore

    vs = PcidVectorStore(...)
    enriched_records = match_pcid_batch(records, vs)

Each output record gets:
    - "pcid" (str or None)
    - "pcid_score" (float or None)
    - "pcid_method" (str: "vector", "fallback", "none")
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Protocol, Sequence, Tuple

import logging

from src.common.logging_utils import sanitize_for_log, safe_log

log = logging.getLogger("pcid-matching")


# --- Vector store interface -------------------------------------------------


class PcidVectorStore(Protocol):
    """
    Minimal interface that any PCID vector store must implement.

    Implementations may:
        - query a DB
        - call a remote API
        - use FAISS / PgVector / etc.
    """

    def search(self, query_text: str, top_k: int = 5) -> Sequence[Tuple[str, float]]:
        """
        Return a list of (pcid, score) pairs, sorted by descending score.

        Score is typically cosine similarity or something in [0, 1].
        """
        ...


@dataclass
class PcidMatchResult:
    pcid: Optional[str]
    score: Optional[float]
    method: str  # "vector", "fallback", "none"
    candidates: Sequence[Tuple[str, float]]


# --- Helpers to build query text -------------------------------------------


def _safe_get(record: Dict[str, Any], key: str) -> str:
    value = record.get(key)
    if value is None:
        return ""
    return str(value).strip()


def build_pcid_query_text(record: Dict[str, Any]) -> str:
    """
    Build a compact text description of a product for PCID matching.

    We intentionally keep this simple and deterministic; all heavy lifting
    (embeddings, similarity) is delegated to the vector store.
    """
    parts: List[str] = []

    # Prefer normalized fields if present; otherwise fallback to raw.
    name = record.get("name_norm") or record.get("name")
    molecule = record.get("molecule_norm") or record.get("molecule")
    strength = record.get("strength_norm") or record.get("strength")
    unit = record.get("unit_norm") or record.get("unit")
    pack_size = record.get("pack_size_norm") or record.get("pack_size")
    route = record.get("route_norm") or record.get("route")
    company = record.get("company_norm") or record.get("company")
    country = record.get("country") or record.get("country_code")

    if name:
        parts.append(f"name: {name}")
    if molecule:
        parts.append(f"molecule: {molecule}")
    if strength or unit:
        parts.append(f"strength: {strength} {unit}".strip())
    if pack_size:
        parts.append(f"pack: {pack_size}")
    if route:
        parts.append(f"route: {route}")
    if company:
        parts.append(f"company: {company}")
    if country:
        parts.append(f"country: {country}")

    # Fallback – ensure we never produce an empty query
    if not parts:
        # last resort: serialize whole record shallowly
        parts.append(" ".join(f"{k}={v}" for k, v in record.items() if isinstance(v, (str, int, float))))

    return " | ".join(parts)


# --- Core matching logic ----------------------------------------------------


def match_pcid_for_record(
    record: Dict[str, Any],
    vector_store: PcidVectorStore,
    *,
    min_score: float = 0.6,
    top_k: int = 5,
) -> PcidMatchResult:
    """
    Match a single record to a PCID using the provided vector store.

    Returns:
        PcidMatchResult with:
            - pcid (or None)
            - score (or None)
            - method ("vector" or "none")
            - candidates (list of (pcid, score))

    It is designed to **never raise** for normal failures; if anything goes
    wrong, we log and return a "none" result.
    """
    query_text = build_pcid_query_text(record)

    try:
        candidates = list(vector_store.search(query_text, top_k=top_k))
    except Exception as exc:
        safe_log(
            log,
            "error",
            "PCID search failed for record",
            extra=sanitize_for_log(
                {"record_id": record.get("id"), "product_url": record.get("product_url"), "error": str(exc)}
            ),
        )
        return PcidMatchResult(
            pcid=None,
            score=None,
            method="none-error",
            candidates=(),
        )

    if not candidates:
        return PcidMatchResult(
            pcid=None,
            score=None,
            method="none",
            candidates=(),
        )

    best_pcid, best_score = candidates[0]

    if best_score < min_score:
        # below threshold – report no match, but keep candidates for debugging
        return PcidMatchResult(
            pcid=None,
            score=best_score,
            method="none-below-threshold",
            candidates=candidates,
        )

    return PcidMatchResult(
        pcid=best_pcid,
        score=best_score,
        method="vector",
        candidates=candidates,
    )


def match_pcid_batch(
    records: Iterable[Dict[str, Any]],
    vector_store: PcidVectorStore,
    *,
    min_score: float = 0.6,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Batch version: iterate over records, attach PCID fields and return a new list.

    Each output record gets new keys:
        - "pcid"
        - "pcid_score"
        - "pcid_method"

    We keep the original record fields intact.
    """
    enriched: List[Dict[str, Any]] = []

    for rec in records:
        match = match_pcid_for_record(rec, vector_store, min_score=min_score, top_k=top_k)

        out = dict(rec)
        out["pcid"] = match.pcid
        out["pcid_score"] = match.score
        out["pcid_method"] = match.method
        # if you want full candidate list, you can also attach it here:
        # out["_pcid_candidates"] = [{"pcid": pc, "score": sc} for pc, sc in match.candidates]

        enriched.append(out)

    return enriched


class _NullVectorStore(PcidVectorStore):
    """Placeholder vector store that returns no candidates."""

    def search(self, query_text: str, top_k: int = 5) -> Sequence[Tuple[str, float]]:
        return []


def match_pcids(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convenience wrapper for callers without an explicit vector store.

    This uses a null vector store to keep the plugin façade functional without
    failing with AttributeError.
    """

    return match_pcid_batch([record], vector_store=_NullVectorStore())
