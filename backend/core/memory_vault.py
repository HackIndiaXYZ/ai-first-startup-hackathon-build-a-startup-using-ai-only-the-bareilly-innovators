import os
import json
import logging

logger = logging.getLogger("sivi.memory_vault")

class MemoryVault:
    def __init__(self):
        self.memory_file = os.path.join(os.path.dirname(__file__), "..", "sivi_memory.json")
        self.memories = []
        self.load_memories()

    def load_memories(self):
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    self.memories = json.load(f)
            except Exception as e:
                logger.error(f"Error loading memory: {e}")
                self.memories = []
        else:
            self.memories = []

    def save_memories(self):
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memories, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving memory: {e}")

    def remember(self, fact: str) -> str:
        """Add a new fact to memory."""
        if fact not in self.memories:
            self.memories.append(fact)
            self.save_memories()
            return "Got it, I will remember that for you."
        return "I already have that in my memory."

    def forget_all(self) -> str:
        """Clear all memories."""
        self.memories = []
        self.save_memories()
        return "I have cleared my memory vault."

    def get_memory_context(self) -> str:
        """Returns the memory block to inject into the system prompt."""
        if not self.memories:
            return ""
        return "THINGS YOU MUST REMEMBER ABOUT THE USER:\n- " + "\n- ".join(self.memories)

memory_vault = MemoryVault()
