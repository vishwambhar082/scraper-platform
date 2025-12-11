from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Callable, Dict, Iterable, Optional

from src.common.logging_utils import get_logger

log = get_logger("plugin-registry")


@dataclass
class Plugin:
    """Description of a loadable plugin."""

    name: str
    module: str
    entrypoint: str
    type: str
    description: str = ""

    def load(self) -> Callable:
        module_obj = import_module(self.module)
        try:
            return getattr(module_obj, self.entrypoint)
        except AttributeError as exc:  # pragma: no cover - defensive guard
            raise ImportError(f"Entrypoint '{self.entrypoint}' missing from module '{self.module}'") from exc


class PluginRegistry:
    """In-memory registry to list and resolve plugins by name and type."""

    def __init__(self, plugins: Optional[Iterable[Plugin]] = None) -> None:
        self._plugins: Dict[str, Plugin] = {}
        for plugin in plugins or []:
            self.register(plugin)

    def register(self, plugin: Plugin) -> None:
        log.debug("Registering plugin", extra={"name": plugin.name, "type": plugin.type})
        self._plugins[plugin.name] = plugin

    def get(self, name: str) -> Optional[Plugin]:
        return self._plugins.get(name)

    def load(self, name: str) -> Callable:
        plugin = self.get(name)
        if not plugin:
            raise KeyError(f"Plugin '{name}' is not registered")
        return plugin.load()

    def list(self) -> Dict[str, Plugin]:
        return dict(self._plugins)

    def by_type(self, plugin_type: str) -> Dict[str, Plugin]:
        return {name: plugin for name, plugin in self._plugins.items() if plugin.type == plugin_type}


from src.plugins.catalog import BUILTIN_PLUGINS  # noqa: E402  - avoid circular import during class definitions


def bootstrap_builtin_plugins() -> PluginRegistry:
    """Return a registry pre-populated with builtin scraper/engine/processor plugins."""

    return PluginRegistry(BUILTIN_PLUGINS)
