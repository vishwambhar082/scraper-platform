from __future__ import annotations

from typing import Any, Dict

from src.core_kernel.models import NormalizedRecord, RawRecord


def unify_record(raw: RawRecord | Dict) -> Dict[str, Any]:
    """Normalize a raw extracted record into the canonical format.

    Args:
        raw: Raw scraper payload as a ``RawRecord`` instance or plain dictionary.

    Returns:
        ``NormalizedRecord`` with standardized field names and parsed types.
    """

    raw_model = raw if isinstance(raw, RawRecord) else RawRecord.model_validate(raw)
    product_url = raw_model.product_url or raw_model.item_url or raw_model.url
    raw_price = raw_model.price
    price = float(raw_price) if raw_price is not None else None

    normalized = NormalizedRecord(
        product_url=product_url,
        name=raw_model.name,
        price=price,
        currency=raw_model.currency or "ARS",
        company=raw_model.company,
        source=raw_model.source,
    )

    return normalized.model_dump()
