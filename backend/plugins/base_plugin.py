"""
SIVI AI  Base Plugin Abstract Class
All plugins must extend this class.
"""

from abc import ABC, abstractmethod


class BasePlugin(ABC):
    @abstractmethod
    def get_name(self) -> str:
        """Return the human-readable name of the plugin."""
        ...

    @abstractmethod
    def get_commands(self) -> list[str]:
        """Return a list of command keywords this plugin handles."""
        ...

    @abstractmethod
    def execute(self, command: str, args: str) -> str:
        """Execute a command and return the spoken response."""
        ...

    def on_load(self):
        """Called when plugin is loaded."""
        pass

    def on_unload(self):
        """Called when plugin is unloaded."""
        pass
