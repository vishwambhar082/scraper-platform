# src/processors/translation_dictionary.py

from typing import Dict, Optional

# Simple in-memory mapping. Extend as needed.
_FIELD_MAP: Dict[str, Dict[str, str]] = {
    "currency": {
        "ars": "ARS",
        "peso": "ARS",
        "pesos": "ARS",
    },
}


def translate_value(field: str, raw_value: str) -> Optional[str]:
    """
    Normalize a raw value using a per-field dictionary.
    Returns the mapped value or the original raw_value if no mapping found.
    """
    if raw_value is None:
        return None
    mapping = _FIELD_MAP.get(field.lower())
    if not mapping:
        return raw_value
    return mapping.get(raw_value.lower(), raw_value)
