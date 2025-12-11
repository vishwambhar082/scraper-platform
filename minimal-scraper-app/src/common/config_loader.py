from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

from src.common.logging_utils import get_logger
from src.common.paths import CONFIG_DIR
from src.common.settings import get_runtime_env

log = get_logger("config-loader")

# These keys ensure the platform has the minimum sections expected by the
# v4.9 blueprint: runtime, logging, and scraping behavior.
REQUIRED_TOP_LEVEL_KEYS = ("app", "logging", "scraping")
REQUIRED_SECTION_FIELDS = {
    "app": ("name", "environment"),
    "logging": ("level",),
    "scraping": ("max_retries",),
}

# Minimal per-source requirements so pipelines can validate expectations early.
REQUIRED_SOURCE_FIELDS = ("source", "engine")


def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing config file: {path}")
    text = path.read_text(encoding="utf-8")

    try:
        data = yaml.safe_load(text)
    except Exception as exc:
        raise ValueError(f"Failed to parse YAML at {path}: {exc}") from exc

    if data is None:
        return {}

    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")

    return data


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _validate(config: Dict[str, Any]) -> None:
    missing = [k for k in REQUIRED_TOP_LEVEL_KEYS if k not in config]
    if missing:
        raise ValueError(f"Config missing required sections: {', '.join(missing)}")

    missing_fields: list[str] = []
    for section, fields in REQUIRED_SECTION_FIELDS.items():
        section_data = config.get(section, {}) or {}
        if not isinstance(section_data, dict):
            missing_fields.extend(f"{section}.{field}" for field in fields)
            continue

        for field in fields:
            if section_data.get(field) in (None, ""):
                missing_fields.append(f"{section}.{field}")

    if missing_fields:
        raise ValueError(
            "Config missing required fields: " + ", ".join(sorted(missing_fields))
        )



def load_config(env: str | None = None, *, config_dir: Path = CONFIG_DIR) -> Dict[str, Any]:
    """Load the global settings.yaml merged with an optional environment overlay.

    Args:
        env: The environment name (e.g., ``dev``, ``staging``, ``prod``). If
            ``None``, the environment from ``settings.yaml`` is used.
        config_dir: Base directory containing ``settings.yaml`` and ``env/``.

    Returns:
        A dictionary combining base settings with environment overrides.

    Raises:
        FileNotFoundError: When a referenced config file cannot be located.
        ValueError: When the loaded config is missing required sections.
    """

    base_path = config_dir / "settings.yaml"
    config = _read_yaml(base_path)

    env_name = env if env is not None else get_runtime_env(default=None)

    if env_name:
        log.info("Using environment '%s' from runtime settings", env_name)
    else:
        env_name = config.get("app", {}).get("environment")

    if env_name:
        env_path = config_dir / "env" / f"{env_name}.yaml"
        log.info("Loading environment overrides from %s", env_path)
        env_config = _read_yaml(env_path)
        config = _deep_merge(config, env_config)

    _validate(config)
    return config


def load_source_config(source: str, *, config_dir: Path = CONFIG_DIR) -> Dict[str, Any]:
    """Load a single source configuration file and validate required fields.

    Args:
        source: Source name (e.g., ``alfabeta``).
        config_dir: Base config directory containing ``sources/<source>.yaml``.

    Returns:
        Parsed YAML content for the source.

    Raises:
        FileNotFoundError: If the source file is missing.
        ValueError: If required fields are missing or the ``source`` field mismatches.
    """

    path = config_dir / "sources" / f"{source}.yaml"
    log.info("Loading source config for %s from %s", source, path)
    source_cfg = _read_yaml(path)

    missing = [field for field in REQUIRED_SOURCE_FIELDS if field not in source_cfg]
    if missing:
        raise ValueError(
            f"Source config {path} missing required fields: {', '.join(missing)}"
        )

    if source_cfg.get("source") != source:
        raise ValueError(
            f"Source config mismatch: expected '{source}' but found '{source_cfg.get('source')}'"
        )

    return source_cfg


__all__ = ["load_config", "load_source_config"]
