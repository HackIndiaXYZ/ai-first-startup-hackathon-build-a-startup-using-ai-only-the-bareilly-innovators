"""
TITAN AI  Plugin Manager
Dynamically discovers, loads, and manages plugins from the plugins/ directory.
"""

import os
import sys
import json
import importlib
from pathlib import Path

# Add plugins dir to path
PLUGINS_DIR = os.path.join(os.path.dirname(__file__), "..", "plugins")
sys.path.insert(0, PLUGINS_DIR)

from base_plugin import BasePlugin


class PluginManager:
    def __init__(self):
        self.plugins: dict[str, BasePlugin] = {}
        self.command_map: dict[str, BasePlugin] = {}
        self._discover_and_load()

    def _discover_and_load(self):
        """Scan plugins/ directory for valid plugin folders."""
        plugins_path = Path(PLUGINS_DIR)
        if not plugins_path.exists():
            return

        for folder in plugins_path.iterdir():
            if not folder.is_dir() or folder.name.startswith("_"):
                continue
            config_path = folder / "config.json"
            plugin_file = folder / "plugin.py"

            if not plugin_file.exists():
                continue

            # Read config if it exists
            enabled = True
            if config_path.exists():
                try:
                    config = json.loads(config_path.read_text())
                    enabled = config.get("enabled", True)
                except Exception:
                    pass

            if not enabled:
                continue

            # Dynamic import
            try:
                module_name = f"{folder.name}.plugin"
                spec = importlib.util.spec_from_file_location(module_name, str(plugin_file))
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Find the plugin class (first subclass of BasePlugin)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, BasePlugin) and attr is not BasePlugin:
                        instance = attr()
                        self.plugins[instance.get_name()] = instance
                        for cmd in instance.get_commands():
                            self.command_map[cmd.lower()] = instance
                        instance.on_load()
                        print(f" Plugin loaded: {instance.get_name()}")
                        break
            except Exception as e:
                print(f" Failed to load plugin '{folder.name}': {e}")

    def try_handle(self, text: str) -> str | None:
        """Check if any plugin can handle this command."""
        for keyword, plugin in self.command_map.items():
            if keyword in text:
                args = text.replace(keyword, "").strip()
                try:
                    return plugin.execute(keyword, args)
                except Exception as e:
                    return f"Plugin error: {e}"
        return None

    def list_plugins(self) -> str:
        if not self.plugins:
            return "No plugins installed."
        names = ", ".join(self.plugins.keys())
        return f"Installed plugins: {names}"

    def enable_plugin(self, name: str) -> str:
        return f"Plugin '{name}' enabled."

    def disable_plugin(self, name: str) -> str:
        if name in self.plugins:
            del self.plugins[name]
            return f"Plugin '{name}' disabled."
        return f"Plugin '{name}' not found."

    def reload_all(self) -> str:
        self.plugins.clear()
        self.command_map.clear()
        self._discover_and_load()
        return f"Reloaded. {len(self.plugins)} plugins active."


plugin_manager = PluginManager()
