from __future__ import annotations

from typing import Any, Dict
import logging
import os
import yaml

from .base import AgentContext
from .registry import run_pipeline

logger = logging.getLogger(__name__)


def _config_base_dir() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def load_agent_config() -> Dict[str, Any]:
    """Load YAML configuration for pipeline definitions."""

    base = _config_base_dir()
    path = os.path.join(base, "config", "pipeline_pack", "pipelines.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_configured_pipeline(
    source: str,
    env: str = "dev",
    **kwargs: Any,
) -> AgentContext:
    cfg = load_agent_config()
    if "sources" not in cfg or source not in cfg["sources"]:
        raise ValueError(f"No agent pipeline configured for source={source!r}")

    source_cfg = cfg["sources"][source]
    defaults = source_cfg.get("defaults", {})
    pipeline = source_cfg["pipeline"]

    ctx = AgentContext(source=source, env=env)
    for k, v in kwargs.items():
        setattr(ctx, k, v)

    logger.info("Running configured pipeline for source=%s env=%s", source, env)
    ctx = run_pipeline(pipeline, ctx, default_agent_config=defaults)
    return ctx


__all__ = ["run_configured_pipeline", "load_agent_config"]
