from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from src.common.logging_utils import get_logger

log = get_logger("schema-registry")

_SCHEMA_REGISTRY: Dict[str, Dict[str, Any]] = {}


DEFAULT_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "product_record": {
        "required_fields": [
            "product_url",
            "name",
            "price",
            "currency",
            "company",
        ],
        "optional_fields": ["description", "run_id", "_version"],
    }
}


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("Failed to load schema from %s: %s", path, exc)
        return {}


try:
    import json  # placed after logger for clarity
except Exception:  # pragma: no cover - extremely unlikely
    json = None  # type: ignore


def register_schema(name: str, schema: Dict[str, Any]) -> None:
    _SCHEMA_REGISTRY[name] = schema


def get_schema(name: str) -> Dict[str, Any] | None:
    return _SCHEMA_REGISTRY.get(name)


def load_default_schemas(config_dir: Path | None = None) -> None:
    """Load built-in schemas and optional JSON definitions from a config dir."""

    if not _SCHEMA_REGISTRY:
        for key, schema in DEFAULT_SCHEMAS.items():
            register_schema(key, schema)

    if not config_dir:
        return

    for path in config_dir.glob("*.schema.json"):
        schema = _load_json(path)
        if schema:
            register_schema(path.stem, schema)
            log.info("Registered schema from %s", path)
