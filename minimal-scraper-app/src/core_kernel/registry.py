from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import yaml

from src.common.logging_utils import get_logger

log = get_logger("component-registry")


@dataclass
class Component:
    """Component metadata discovered from the registry YAML."""

    name: str
    module: str
    callable: str
    type: str = "function"
    description: str = ""

    def load_callable(self) -> Callable[..., Any]:
        """Import the configured callable for this component.

        Returns:
            A Python callable resolved from ``module`` and ``callable``.

        Raises:
            ImportError: If the module or callable cannot be imported.
        """

        module_obj = import_module(self.module)
        try:
            return getattr(module_obj, self.callable)
        except AttributeError as exc:  # pragma: no cover - defensive guard
            raise ImportError(f"Callable '{self.callable}' missing from module '{self.module}'") from exc


class ComponentRegistry:
    """Registry for pipeline components declared in YAML."""

    def __init__(self) -> None:
        self._components: Dict[str, Component] = {}

    @classmethod
    def from_yaml(cls, path: Path) -> "ComponentRegistry":
        """Load a registry from a YAML file on disk.

        Args:
            path: Path to the YAML registry file.

        Returns:
            A populated :class:`ComponentRegistry` instance. Missing files
            produce an empty registry and log a warning.
        """

        registry = cls()
        if not path.exists():
            log.warning("Component definition file %s not found; registry will be empty", path)
            return registry

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for name, meta in (data.get("components") or {}).items():
            registry.register(
                name=name,
                module=meta.get("module"),
                callable_name=meta.get("callable"),
                type=meta.get("type", "function"),
                description=meta.get("description", ""),
            )
        return registry

    def register(
        self,
        name: str,
        module: str,
        callable_name: str,
        type: str = "function",
        description: str = "",
    ) -> None:
        """Register a component in memory without persisting to disk.

        Args:
            name: Registry name of the component.
            module: Python module path containing the callable.
            callable_name: Symbol name of the callable within the module.
            type: Component type metadata for pipeline introspection.
            description: Human-readable description of the component.

        Raises:
            ValueError: If any required field is missing.
        """

        if not all([name, module, callable_name]):
            raise ValueError("Component registration requires name, module, and callable")

        self._components[name] = Component(
            name=name,
            module=module,
            callable=callable_name,
            type=type,
            description=description,
        )
        log.debug("Registered component %s -> %s.%s", name, module, callable_name)

    def get(self, name: str) -> Optional[Component]:
        """Retrieve a component by name if registered."""

        return self._components.get(name)

    def resolve_callable(self, name: str) -> Callable[..., Any]:
        """Return a callable for a registered component name.

        Args:
            name: Name used to register the component.

        Returns:
            Callable referenced by the registry entry.

        Raises:
            KeyError: If the component name is not registered.
        """

        component = self.get(name)
        if not component:
            raise KeyError(f"Component '{name}' is not registered")
        return component.load_callable()

    def list_components(self) -> Dict[str, Component]:
        """Return a shallow copy of all registered components."""

        return dict(self._components)
