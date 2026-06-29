"""
Sivi — Todo Plugin
Manages a simple local to-do list.
"""

import os
import json
import logging
from plugins.base_plugin import SiviPlugin

logger = logging.getLogger("sivi.plugins.todo")

class TodoPlugin(SiviPlugin):
    def __init__(self):
        self.todo_file = os.path.join(os.path.dirname(__file__), "..", "data", "todos.json")
        self._ensure_file()

    @property
    def name(self) -> str:
        return "todo_plugin"
        
    @property
    def description(self) -> str:
        return "Manages a simple local to-do list."
        
    def get_supported_commands(self) -> list[str]:
        return [
            r"add (?P<task>.*) to my to-do list",
            r"add (?P<task>.*) to my todo list",
            r"read my to-do list",
            r"read my todo list",
            r"clear my to-do list",
            r"clear my todo list"
        ]
        
    def _ensure_file(self):
        os.makedirs(os.path.dirname(self.todo_file), exist_ok=True)
        if not os.path.exists(self.todo_file):
            with open(self.todo_file, "w") as f:
                json.dump([], f)

    def _load_todos(self) -> list[str]:
        try:
            with open(self.todo_file, "r") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_todos(self, todos: list[str]):
        try:
            with open(self.todo_file, "w") as f:
                json.dump(todos, f)
        except Exception as e:
            logger.error(f"Error saving todos: {e}")
        
    def execute(self, command: str, **kwargs) -> str:
        task = kwargs.get("task")
        
        if "add" in command.lower():
            if not task:
                return "Please specify what you want to add."
            todos = self._load_todos()
            todos.append(task)
            self._save_todos(todos)
            return f"Added '{task}' to your list."
            
        elif "read" in command.lower():
            todos = self._load_todos()
            if not todos:
                return "Your to-do list is empty."
            todo_str = ", ".join(todos)
            return f"You have {len(todos)} tasks: {todo_str}."
            
        elif "clear" in command.lower():
            self._save_todos([])
            return "I have cleared your to-do list."
            
        return "Command not recognized by Todo Plugin."
