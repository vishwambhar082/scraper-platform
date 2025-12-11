from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import jsonschema
import yaml
from jsonschema import ValidationError

from src.common.logging_utils import get_logger
from src.core_kernel.registry import Component, ComponentRegistry

log = get_logger(__name__)

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "dsl" / "schema" / "pipeline_schema.json"


@dataclass
class CompiledStep:
    """Prepared pipeline step with resolved component metadata."""

    id: str
    component: Component
    params: Dict[str, Any]
    depends_on: List[str]
    step_type: str


@dataclass
class CompiledPipeline:
    """Pipeline ready for execution by :class:`ExecutionEngine`."""

    name: str
    description: str
    steps: List[CompiledStep]
    variants: List["PipelineVariant"]


@dataclass
class PipelineVariant:
    """Configuration wrapper for an individual scraper experiment variant."""

    id: str
    description: str = ""
    params: Dict[str, Any] = field(default_factory=dict)


def _load_pipeline_yaml(path: Path) -> Dict[str, Any]:
    """Read and parse a pipeline YAML file from disk."""

    if not path.exists():
        raise FileNotFoundError(f"Pipeline definition not found at {path}")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive logging
        raise ValueError(f"Failed to parse pipeline YAML at {path}: {exc}") from exc

    if raw is None:
        return {}

    if not isinstance(raw, dict):
        raise ValueError(f"Pipeline YAML must be a mapping at {path}")

    return raw


def _load_pipeline_schema() -> Dict[str, Any]:
    """Load the JSON schema used to validate pipeline DSL definitions."""

    with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _validate_pipeline(raw: Dict[str, Any], path: Path) -> None:
    """Validate parsed pipeline YAML against the DSL schema."""

    schema = _load_pipeline_schema()
    try:
        jsonschema.validate(instance=raw, schema=schema)
    except ValidationError as exc:
        msg = f"Invalid DSL pipeline '{path}': {exc.message} at {list(exc.path)}"
        log.error(msg, extra={"pipeline_path": str(path)})
        raise ValueError(msg) from exc


class PipelineCompiler:
    """Compile pipeline DSL files into executable structures."""

    def __init__(self, registry: ComponentRegistry):
        self.registry = registry

    def compile_from_file(self, pipeline_path: Path) -> CompiledPipeline:
        """Compile a pipeline definition into a :class:`CompiledPipeline`.

        Args:
            pipeline_path: Path to the YAML DSL file describing the pipeline.

        Returns:
            Fully compiled pipeline with resolved components.

        Raises:
            ValueError: If validation fails or the pipeline is missing steps.
        """

        raw = _load_pipeline_yaml(pipeline_path)
        _validate_pipeline(raw, pipeline_path)

        pipeline_block = raw.get("pipeline") or {}
        name = pipeline_block.get("name") or pipeline_path.stem
        description = pipeline_block.get("description", "")
        variants: List[PipelineVariant] = []
        for variant in pipeline_block.get("variants", []) or []:
            if not isinstance(variant, dict):
                raise ValueError(f"Variant entries must be mappings in pipeline {name}")
            variant_id = variant.get("id")
            if not variant_id:
                raise ValueError(f"Variant in pipeline {name} is missing required 'id'")
            variants.append(
                PipelineVariant(
                    id=variant_id,
                    description=variant.get("description", ""),
                    params=variant.get("params") or {},
                )
            )

        steps: List[CompiledStep] = []

        for step in pipeline_block.get("steps", []):
            component_name = step.get("component")
            component = self.registry.get(component_name)
            if not component:
                raise ValueError(f"Component '{component_name}' referenced in pipeline is not registered")

            depends_on = step.get("depends_on") or []
            if not isinstance(depends_on, list):
                raise ValueError(f"Step '{step.get('id') or component_name}' depends_on must be a list")

            compiled_step = CompiledStep(
                id=step.get("id") or component_name,
                component=component,
                params=step.get("params") or {},
                depends_on=list(depends_on),
                step_type=step.get("type") or component.type,
            )
            steps.append(compiled_step)
            log.debug("Compiled step %s using component %s", compiled_step.id, component_name)

        if not steps:
            raise ValueError(f"Pipeline {name} has no steps defined")

        return CompiledPipeline(name=name, description=description, steps=steps, variants=variants)
