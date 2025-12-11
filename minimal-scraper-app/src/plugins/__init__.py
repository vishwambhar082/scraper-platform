"""Plugin registry providing stable aliases for scrapers, engines, and processors.

The plugin layout mirrors the v4.9 blueprint so external callers can resolve
callables under the ``src.plugins`` namespace without importing internal
packages directly. Each plugin is described by name, type, module path, and
entrypoint to keep discovery and loading explicit.
"""

from .registry import Plugin, PluginRegistry, bootstrap_builtin_plugins

__all__ = ["Plugin", "PluginRegistry", "bootstrap_builtin_plugins"]
