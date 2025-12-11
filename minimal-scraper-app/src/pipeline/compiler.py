"""Pipeline compiler that transforms YAML definitions into executable pipelines."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import jsonschema
import yaml

from src.common.logging_utils import get_logger
from .registry import UnifiedRegistry
from .step import PipelineStep, StepType

log = get_logger("pipeline.compiler")


@dataclass
class CompiledPipeline:
    """A compiled pipeline ready for execution."""
    
    name: str
    description: str
    steps: List[PipelineStep]
    variants: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class PipelineCompiler:
    """Compiles YAML pipeline definitions into executable pipelines."""
    
    def __init__(self, registry: UnifiedRegistry):
        self.registry = registry
        
    def compile_from_file(self, path: Path) -> CompiledPipeline:
        """Compile a pipeline from a YAML file.
        
        Args:
            path: Path to pipeline YAML file
            
        Returns:
            CompiledPipeline ready for execution
        """
        if not path.exists():
            raise FileNotFoundError(f"Pipeline file not found: {path}")
            
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not raw:
            raise ValueError(f"Empty pipeline file: {path}")
            
        return self.compile(raw, path.stem)
        
    def compile(self, raw: Dict[str, Any], name: str = "pipeline") -> CompiledPipeline:
        """Compile a pipeline from raw dict.
        
        Args:
            raw: Raw pipeline definition
            name: Pipeline name
            
        Returns:
            CompiledPipeline
        """
        pipeline_def = raw.get("pipeline", {})
        
        pipeline_name = pipeline_def.get("name", name)
        description = pipeline_def.get("description", "")
        variants = pipeline_def.get("variants", [])
        
        # Compile steps
        steps: List[PipelineStep] = []
        for step_def in pipeline_def.get("steps", []):
            step = self._compile_step(step_def)
            steps.append(step)
            
        if not steps:
            raise ValueError(f"Pipeline {pipeline_name} has no steps")
            
        log.info("Compiled pipeline '%s' with %d steps", pipeline_name, len(steps))
        
        return CompiledPipeline(
            name=pipeline_name,
            description=description,
            steps=steps,
            variants=variants,
            metadata={"source_file": name},
        )
        
    def _compile_step(self, step_def: Dict[str, Any]) -> PipelineStep:
        """Compile a single step definition."""
        component_name = step_def.get("component")
        if not component_name:
            raise ValueError(f"Step missing 'component': {step_def}")
            
        component = self.registry.get(component_name)
        if not component:
            raise ValueError(f"Component '{component_name}' not registered")
            
        step_id = step_def.get("id", component_name)
        step_type = self._resolve_step_type(step_def.get("type") or component.type)
        
        return PipelineStep(
            id=step_id,
            type=step_type,
            callable=component.load(),
            params=step_def.get("params", {}),
            depends_on=step_def.get("depends_on", []),
            description=step_def.get("description", component.description),
            retry_count=step_def.get("retry", 0),
            timeout=step_def.get("timeout"),
            required=step_def.get("required", True),
        )
        
    def _resolve_step_type(self, type_str: str) -> StepType:
        """Map string type to StepType enum."""
        type_map = {
            "fetch": StepType.FETCH,
            "http": StepType.FETCH,
            "parse": StepType.PARSE,
            "transform": StepType.TRANSFORM,
            "validate": StepType.VALIDATE,
            "qc": StepType.VALIDATE,
            "enrich": StepType.ENRICH,
            "llm": StepType.ENRICH,
            "pcid": StepType.ENRICH,
            "export": StepType.EXPORT,
            "agent": StepType.AGENT,
        }
        return type_map.get(type_str.lower(), StepType.CUSTOM)
