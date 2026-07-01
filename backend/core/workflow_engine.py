"""
SIVI AI — Workflow Engine (Macro Command Runner)
Allows users to define and execute named multi-step command sequences.
Example: "good morning routine" -> [open chrome, check weather, read calendar, play news]
"""

import os
import json
import logging
from dataclasses import dataclass, field

logger = logging.getLogger("sivi.workflow")

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
WORKFLOW_FILE = os.path.join(DATA_DIR, "sivi_workflows.json")

# Built-in default workflows
DEFAULT_WORKFLOWS: dict[str, list[str]] = {
    "good morning routine": [
        "OPEN_APP chrome",
        "CALENDAR_EVENTS",
        "NEWS",
    ],
    "work mode": [
        "OPEN_APP vscode",
        "MUTE",
        "BRIGHTNESS_UP",
    ],
    "night mode": [
        "BRIGHTNESS_DOWN",
        "MUTE",
        "SLEEP",
    ],
    "focus mode": [
        "MUTE",
        "BRIGHTNESS_DOWN",
        "OPEN_APP vscode",
    ],
}

class WorkflowEngine:
    """
    Stores and executes named multi-step command sequences (macros).
    User-defined macros are persisted to data/sivi_workflows.json.
    """

    def __init__(self):
        self.workflows: dict[str, list[str]] = dict(DEFAULT_WORKFLOWS)
        self._load()

    def _load(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.exists(WORKFLOW_FILE):
            try:
                with open(WORKFLOW_FILE, "r", encoding="utf-8") as f:
                    user_workflows = json.load(f)
                self.workflows.update(user_workflows)
                logger.info(f"[WorkflowEngine] Loaded {len(user_workflows)} user workflows")
            except Exception as e:
                logger.error(f"[WorkflowEngine] Failed to load workflows: {e}")

    def _save(self):
        # Only save user-defined (non-default) workflows
        user_only = {k: v for k, v in self.workflows.items() if k not in DEFAULT_WORKFLOWS}
        try:
            with open(WORKFLOW_FILE, "w", encoding="utf-8") as f:
                json.dump(user_only, f, indent=2)
        except Exception as e:
            logger.error(f"[WorkflowEngine] Failed to save workflows: {e}")

    def add_workflow(self, name: str, commands: list[str]) -> str:
        """Define a new named macro."""
        self.workflows[name.lower().strip()] = commands
        self._save()
        logger.info(f"[WorkflowEngine] Saved workflow: '{name}' with {len(commands)} steps")
        return f"Workflow '{name}' saved with {len(commands)} step(s)."

    def get_workflow(self, name: str) -> list[str] | None:
        """Return steps for a named workflow, or None if not found."""
        return self.workflows.get(name.lower().strip())

    def list_workflows(self) -> str:
        """Return a human-readable list of all workflows."""
        if not self.workflows:
            return "No workflows defined yet."
        lines = ["Available workflows:"]
        for name, steps in self.workflows.items():
            lines.append(f"  • '{name}' ({len(steps)} step{'s' if len(steps) > 1 else ''})")
        return "\n".join(lines)

    def match_trigger(self, user_text: str) -> str | None:
        """
        Check if the user's text contains a workflow trigger phrase.
        Returns the workflow name if matched, else None.
        """
        text_lower = user_text.lower().strip()
        for name in self.workflows:
            if name in text_lower:
                return name
        return None


# Module-level singleton
workflow_engine = WorkflowEngine()
