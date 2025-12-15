# src/etl/etl_config_loader.py
from __future__ import annotations

import yaml
from typing import Any, Dict

from src.common.paths import CONFIG_DIR


def load_etl_config() -> Dict[str, Any]:
    path = CONFIG_DIR / "etl.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
