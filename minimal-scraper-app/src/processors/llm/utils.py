"""
Utility functions for LLM integration.

Helper functions to determine when and how to use LLM based on config.
"""

from __future__ import annotations

from typing import Any, Dict

from src.processors.hybrid_mode import should_use_llm


def is_llm_enabled(source_config: Dict[str, Any]) -> bool:
    """Check if LLM is enabled for a source."""
    return source_config.get("llm", {}).get("enabled", False)


def get_llm_mode(source_config: Dict[str, Any], stage: str) -> str:
    """
    Get LLM mode for a stage.

    Args:
        source_config: Source config
        stage: Stage name ('extract_engine', 'pdf_to_table', 'normalize', 'qc')

    Returns:
        Mode string: 'none', 'classic', 'llm', or 'hybrid'
    """
    mode = source_config.get("mode", {})

    if stage == "extract_engine":
        return mode.get("extract_engine", "classic")
    elif stage == "pdf_to_table":
        return mode.get("pdf_to_table", "none")
    elif stage == "normalize":
        return "llm" if should_use_llm(source_config, "normalize") else "classic"
    elif stage == "qc":
        return "llm" if should_use_llm(source_config, "qc") else "classic"
    else:
        return "classic"


def should_use_llm_for_stage(source_config: Dict[str, Any], stage: str) -> bool:
    """
    Determine if LLM should be used for a given stage.

    Args:
        source_config: Source config
        stage: Stage name

    Returns:
        True if LLM should be used
    """
    return should_use_llm(source_config, stage)


def get_table_schema(source_config: Dict[str, Any]) -> Dict[str, list[str]]:
    """
    Get table schema from config.

    Args:
        source_config: Source config

    Returns:
        Dict mapping table types to column lists
    """
    return source_config.get("table_schema", {})


def get_llm_config(source_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get LLM configuration section.

    Args:
        source_config: Source config

    Returns:
        LLM config dict (empty if not configured)
    """
    return source_config.get("llm", {})

