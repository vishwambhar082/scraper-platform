"""Unified component registry for pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import yaml

from src.common.logging_utils import get_logger

log = get_logger("pipeline.registry")


@dataclass
class Component:
    """Registry entry for a pipeline component."""
    
    name: str
    module: str
    callable_name: str
    type: str
    description: str = ""
    
    def load(self) -> Callable[..., Any]:
        """Dynamically import and return the callable."""
        try:
            mod = import_module(self.module)
            return getattr(mod, self.callable_name)
        except (ImportError, AttributeError) as exc:
            raise ImportError(
                f"Failed to load {self.callable_name} from {self.module}: {exc}"
            ) from exc


class UnifiedRegistry:
    """Central registry for all pipeline components.
    
    This replaces:
    - core_kernel.registry.ComponentRegistry
    - agents.registry.AgentRegistry  
    - pipeline_pack.agents.registry.AgentRegistry
    """
    
    def __init__(self) -> None:
        self._components: Dict[str, Component] = {}
        
    @classmethod
    def from_yaml(cls, path: Path) -> "UnifiedRegistry":
        """Load registry from YAML file."""
        registry = cls()
        
        if not path.exists():
            log.warning("Registry file not found: %s", path)
            return registry
            
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        components = data.get("components", {})
        
        for name, spec in components.items():
            registry.register(
                name=name,
                module=spec.get("module", ""),
                callable_name=spec.get("callable", ""),
                type=spec.get("type", "custom"),
                description=spec.get("description", ""),
            )
            
        log.info("Loaded %d components from %s", len(registry._components), path)
        return registry
        
    def register(
        self,
        name: str,
        module: str,
        callable_name: str,
        type: str = "custom",
        description: str = "",
    ) -> None:
        """Register a component."""
        if not all([name, module, callable_name]):
            raise ValueError("name, module, and callable_name are required")
            
        self._components[name] = Component(
            name=name,
            module=module,
            callable_name=callable_name,
            type=type,
            description=description,
        )
        log.debug("Registered component: %s -> %s.%s", name, module, callable_name)
        
    def register_callable(
        self,
        name: str,
        callable: Callable[..., Any],
        type: str = "custom",
        description: str = "",
    ) -> None:
        """Register an already-imported callable directly."""
        # Store callable directly by creating a pseudo-component
        component = Component(
            name=name,
            module=callable.__module__,
            callable_name=callable.__name__,
            type=type,
            description=description,
        )
        # Override load to return the callable directly
        component.load = lambda: callable  # type: ignore
        self._components[name] = component
        log.debug("Registered callable: %s (%s)", name, type)
        
    def get(self, name: str) -> Optional[Component]:
        """Get a registered component by name."""
        return self._components.get(name)
        
    def resolve(self, name: str) -> Callable[..., Any]:
        """Resolve and return the callable for a component."""
        component = self.get(name)
        if not component:
            raise KeyError(f"Component '{name}' not registered")
        return component.load()
        
    def list_components(self) -> Dict[str, Component]:
        """Return all registered components."""
        return dict(self._components)
        
    def has(self, name: str) -> bool:
        """Check if a component is registered."""
        return name in self._components
