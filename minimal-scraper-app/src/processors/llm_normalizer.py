"""
LLM-aware normalization utilities.

This module is intentionally written so that it works **without** a real LLM:
- By default it applies deterministic, rule-based cleanup.
- If you pass an LLM callback, it will be used to refine the normalized text.

The idea is:
    raw_record -> unify_fields.unify_record() -> unified_record
    unified_record -> llm_normalizer.normalize_record() -> enriched_record

Where `enriched_record` keeps the original fields and adds:
    - "<field>_norm"      (normalized text)
    - "_norm_meta" block  (per-field confidence + method)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple


# Type for an optional LLM function. It receives a prompt
# and returns a single string with the "best" normalized value.
LLMFn = Callable[[str], str]


@dataclass
class FieldNormalizationMeta:
    """Metadata about how a single field was normalized."""

    confidence: float
    method: str  # e.g. "rules", "llm", "llm+rules"
    original: Optional[str]
    normalized: Optional[str]


def _clean_text(value: Optional[str]) -> Optional[str]:
    """
    Deterministic cleanup that is safe to run without any model:

    - strip leading/trailing whitespace
    - collapse repeated spaces
    - normalize some common punctuation
    - keep original capitalization meaningful, but fix shouting
    """
    if value is None:
        return value
    text = value.strip()
    # collapse whitespace
    while "  " in text:
        text = text.replace("  ", " ")

    # avoid ALL CAPS unless it's very short (like "AR", "ML")
    if len(text) > 4 and text.isupper():
        text = text.title()

    return text


def _maybe_llm_refine(
    field_name: str,
    cleaned_value: Optional[str],
    llm_fn: Optional[LLMFn],
) -> Tuple[Optional[str], FieldNormalizationMeta]:
    """
    Optionally refine a cleaned field using an LLM.

    If `llm_fn` is None, we stick to rules only.
    """
    if cleaned_value is None:
        meta = FieldNormalizationMeta(
            confidence=0.0,
            method="none",
            original=None,
            normalized=None,
        )
        return None, meta

    if llm_fn is None:
        # Rules-only path
        meta = FieldNormalizationMeta(
            confidence=0.7,
            method="rules",
            original=cleaned_value,
            normalized=cleaned_value,
        )
        return cleaned_value, meta

    # LLM path: we give a lightweight, field-specific instruction.
    prompt = (
        f"Normalize the following {field_name} for a pharma product catalog. "
        f"Return only the cleaned value, no explanations:\n\n{cleaned_value}"
    )
    try:
        llm_out = llm_fn(prompt).strip()
        if not llm_out:
            # fall back to rules
            normalized = cleaned_value
            method = "rules"
            confidence = 0.7
        else:
            normalized = _clean_text(llm_out)
            method = "llm+rules"
            confidence = 0.9
    except Exception:
        # Be absolutely defensive: never let an LLM failure kill the pipeline.
        normalized = cleaned_value
        method = "rules-error-fallback"
        confidence = 0.6

    meta = FieldNormalizationMeta(
        confidence=confidence,
        method=method,
        original=cleaned_value,
        normalized=normalized,
    )
    return normalized, meta


def normalize_record(
    record: Dict[str, Any],
    llm_fn: Optional[LLMFn] = None,
) -> Dict[str, Any]:
    """
    Normalize key textual fields of a unified record.

    Expected input record (after unify_fields.unify_record):

        {
            "product_url": ...,
            "name": ...,
            "price": ...,
            "currency": ...,
            "company": ...,
            "source": ...,
            ...
        }

    Output:
        - Original fields left untouched.
        - Adds:
            - name_norm, company_norm
            - _norm_meta (per-field metadata dict)

    This function is deliberately conservative: if anything goes wrong with
    the LLM, it falls back to pure rule-based cleanup.
    """
    out: Dict[str, Any] = dict(record)  # shallow copy

    norm_meta: Dict[str, FieldNormalizationMeta] = {}

    # Name
    raw_name = record.get("name")
    cleaned_name = _clean_text(raw_name) if raw_name is not None else None
    name_norm, name_meta = _maybe_llm_refine("product name", cleaned_name, llm_fn)
    out["name_norm"] = name_norm
    norm_meta["name"] = name_meta

    # Company
    raw_company = record.get("company")
    cleaned_company = _clean_text(raw_company) if raw_company is not None else None
    company_norm, company_meta = _maybe_llm_refine(
        "company name", cleaned_company, llm_fn
    )
    out["company_norm"] = company_norm
    norm_meta["company"] = company_meta

    # You can extend this later with strength, pack size, route, etc.,
    # once those fields are present in the unified record.

    # Attach normalization metadata in a dedicated key so it can be
    # inspected or written to a separate table if needed.
    out["_norm_meta"] = {field: meta.__dict__ for field, meta in norm_meta.items()}

    return out
