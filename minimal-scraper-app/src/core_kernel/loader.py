# file: src/core_kernel/loader.py
"""
Lightweight loader for DSL pipelines and plugin registrations.

This is intentionally minimal. It provides:
- load_pipeline_config() – load a DSL pipeline definition from YAML
- load_registered_pipeline() – resolve a compiled pipeline from the registry
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict

import yaml  # ensure PyYAML is in requirements

from . import registry


def load_pipeline_config(path: str | Path) -> Dict[str, Any]:
    """
    Load a pipeline YAML file and return the raw dict.

    This is meant to be called by orchestration / CLI tooling before compiling.
    """
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_registered_pipeline(name: str) -> Any:
    """Resolve a registered pipeline by name.

    Args:
        name: Registry identifier for the pipeline.

    Returns:
        Whatever object the registry exposes for the pipeline (callable, class, etc.).

    Raises:
        AttributeError: If the registry module does not expose ``get_pipeline``.
    """

    getter: Callable[[str], Any] | None = getattr(registry, "get_pipeline", None)
    if getter is None:
        raise AttributeError("Registry does not expose get_pipeline")
    return getter(name)
