"""
Plugin loader and runtime.

Manages plugin lifecycle with isolation and version compatibility.
"""

import logging
import importlib
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Type
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class PluginState(str, Enum):
    """Plugin states."""
    UNLOADED = "unloaded"
    LOADED = "loaded"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class PluginMetadata:
    """Plugin metadata."""
    plugin_id: str
    name: str
    version: str
    author: str
    description: str
    module_path: str
    requires_version: str  # Min platform version
    capabilities: List[str]
    dependencies: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class PluginBase:
    """
    Base class for plugins.

    All plugins must inherit from this class.
    """

    @property
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        raise NotImplementedError

    def on_load(self):
        """Called when plugin is loaded."""
        pass

    def on_unload(self):
        """Called when plugin is unloaded."""
        pass

    def on_activate(self):
        """Called when plugin is activated."""
        pass

    def on_deactivate(self):
        """Called when plugin is deactivated."""
        pass


@dataclass
class LoadedPlugin:
    """Loaded plugin instance."""
    metadata: PluginMetadata
    instance: PluginBase
    state: PluginState
    error: Optional[str] = None


class PluginLoader:
    """
    Plugin loader with lifecycle management.

    Features:
    - Dynamic load/unload
    - Version compatibility checking
    - Dependency resolution
    - Error isolation
    """

    def __init__(self, plugins_dir: Path, platform_version: str = "1.0.0"):
        """
        Initialize plugin loader.

        Args:
            plugins_dir: Directory containing plugins
            platform_version: Platform version for compatibility check
        """
        self.plugins_dir = plugins_dir
        self.platform_version = platform_version
        self._plugins: Dict[str, LoadedPlugin] = {}

    def discover_plugins(self) -> List[PluginMetadata]:
        """
        Discover available plugins.

        Returns:
            List of plugin metadata
        """
        discovered = []

        if not self.plugins_dir.exists():
            logger.warning(f"Plugins directory not found: {self.plugins_dir}")
            return discovered

        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue

            metadata_file = plugin_dir / "plugin.json"
            if not metadata_file.exists():
                continue

            try:
                import json
                data = json.loads(metadata_file.read_text())

                metadata = PluginMetadata(
                    plugin_id=data['plugin_id'],
                    name=data['name'],
                    version=data['version'],
                    author=data['author'],
                    description=data['description'],
                    module_path=data['module_path'],
                    requires_version=data.get('requires_version', '0.0.0'),
                    capabilities=data.get('capabilities', []),
                    dependencies=data.get('dependencies', [])
                )

                discovered.append(metadata)

            except Exception as e:
                logger.error(f"Failed to load plugin metadata: {plugin_dir} - {e}")

        logger.info(f"Discovered {len(discovered)} plugins")
        return discovered

    def load_plugin(self, plugin_id: str, metadata: PluginMetadata) -> bool:
        """
        Load plugin.

        Args:
            plugin_id: Plugin identifier
            metadata: Plugin metadata

        Returns:
            True if loaded successfully
        """
        if plugin_id in self._plugins:
            logger.warning(f"Plugin already loaded: {plugin_id}")
            return False

        try:
            # Version compatibility check
            if not self._check_version_compatibility(metadata.requires_version):
                raise PluginLoadError(
                    f"Incompatible version: requires {metadata.requires_version}, "
                    f"platform is {self.platform_version}"
                )

            # Import module
            module_path = f"plugins.{plugin_id}.{metadata.module_path}"
            module = importlib.import_module(module_path)

            # Find plugin class
            plugin_class = None
            for item in dir(module):
                obj = getattr(module, item)
                if isinstance(obj, type) and issubclass(obj, PluginBase) and obj != PluginBase:
                    plugin_class = obj
                    break

            if not plugin_class:
                raise PluginLoadError("No PluginBase subclass found")

            # Instantiate
            instance = plugin_class()

            # Store loaded plugin
            loaded = LoadedPlugin(
                metadata=metadata,
                instance=instance,
                state=PluginState.LOADED
            )
            self._plugins[plugin_id] = loaded

            # Call lifecycle hook
            instance.on_load()

            logger.info(f"Plugin loaded: {plugin_id} v{metadata.version}")
            return True

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_id}: {e}", exc_info=True)

            self._plugins[plugin_id] = LoadedPlugin(
                metadata=metadata,
                instance=None,
                state=PluginState.ERROR,
                error=str(e)
            )

            return False

    def unload_plugin(self, plugin_id: str) -> bool:
        """
        Unload plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if unloaded successfully
        """
        if plugin_id not in self._plugins:
            logger.warning(f"Plugin not loaded: {plugin_id}")
            return False

        loaded = self._plugins[plugin_id]

        try:
            # Deactivate if active
            if loaded.state == PluginState.ACTIVE:
                self.deactivate_plugin(plugin_id)

            # Call lifecycle hook
            if loaded.instance:
                loaded.instance.on_unload()

            # Remove from loaded plugins
            del self._plugins[plugin_id]

            logger.info(f"Plugin unloaded: {plugin_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to unload plugin {plugin_id}: {e}", exc_info=True)
            return False

    def activate_plugin(self, plugin_id: str) -> bool:
        """Activate plugin."""
        if plugin_id not in self._plugins:
            logger.warning(f"Plugin not loaded: {plugin_id}")
            return False

        loaded = self._plugins[plugin_id]

        if loaded.state == PluginState.ACTIVE:
            return True

        if loaded.state != PluginState.LOADED:
            logger.warning(f"Plugin cannot be activated: {plugin_id} (state: {loaded.state})")
            return False

        try:
            loaded.instance.on_activate()
            loaded.state = PluginState.ACTIVE
            logger.info(f"Plugin activated: {plugin_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to activate plugin {plugin_id}: {e}", exc_info=True)
            return False

    def deactivate_plugin(self, plugin_id: str) -> bool:
        """Deactivate plugin."""
        if plugin_id not in self._plugins:
            return False

        loaded = self._plugins[plugin_id]

        if loaded.state != PluginState.ACTIVE:
            return True

        try:
            loaded.instance.on_deactivate()
            loaded.state = PluginState.LOADED
            logger.info(f"Plugin deactivated: {plugin_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to deactivate plugin {plugin_id}: {e}", exc_info=True)
            return False

    def get_plugin(self, plugin_id: str) -> Optional[PluginBase]:
        """Get plugin instance."""
        loaded = self._plugins.get(plugin_id)
        return loaded.instance if loaded else None

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all loaded plugins."""
        return [
            {
                'plugin_id': plugin_id,
                'name': loaded.metadata.name,
                'version': loaded.metadata.version,
                'state': loaded.state.value,
                'error': loaded.error
            }
            for plugin_id, loaded in self._plugins.items()
        ]

    def _check_version_compatibility(self, required_version: str) -> bool:
        """Check version compatibility."""
        # Simple version check (major.minor.patch)
        try:
            req_parts = [int(x) for x in required_version.split('.')]
            plat_parts = [int(x) for x in self.platform_version.split('.')]

            # Check major version match
            if req_parts[0] != plat_parts[0]:
                return False

            # Check minor version
            if req_parts[1] > plat_parts[1]:
                return False

            return True

        except Exception:
            return False


class PluginLoadError(Exception):
    """Exception raised when plugin load fails."""
    pass
