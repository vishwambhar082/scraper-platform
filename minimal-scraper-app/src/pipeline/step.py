"""Pipeline step definitions and execution context."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import time


class StepType(str, Enum):
    """Type classification for pipeline steps."""
    
    FETCH = "fetch"  # HTTP/API requests
    PARSE = "parse"  # HTML/JSON parsing
    TRANSFORM = "transform"  # Data transformation
    VALIDATE = "validate"  # QC/validation
    ENRICH = "enrich"  # LLM normalization, PCID matching
    EXPORT = "export"  # Database, S3, GCS export
    AGENT = "agent"  # AI-powered autonomous step
    CUSTOM = "custom"  # User-defined step


@dataclass
class StepResult:
    """Result of executing a single pipeline step."""
    
    step_id: str
    status: str  # 'success', 'failed', 'skipped'
    duration_seconds: float
    output: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def success(self) -> bool:
        return self.status == "success"


@dataclass
class PipelineStep:
    """Definition of a single pipeline step."""
    
    id: str
    type: StepType
    callable: Callable[..., Any]
    params: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    description: str = ""
    retry_count: int = 0
    timeout: Optional[int] = None
    required: bool = True  # If False, failures won't fail the pipeline
    
    def execute(self, context: Dict[str, Any]) -> StepResult:
        """Execute this step with the given context.
        
        Args:
            context: Runtime context including results from dependencies
            
        Returns:
            StepResult with status and output
        """
        start = time.time()
        
        try:
            # Merge step params with runtime context
            runtime_params = {**self.params, **context}
            
            # Execute the callable
            output = self.callable(**runtime_params) if runtime_params else self.callable()
            
            return StepResult(
                step_id=self.id,
                status="success",
                duration_seconds=time.time() - start,
                output=output,
            )
            
        except Exception as exc:
            return StepResult(
                step_id=self.id,
                status="failed",
                duration_seconds=time.time() - start,
                error=str(exc),
                metadata={"exception_type": type(exc).__name__},
            )
