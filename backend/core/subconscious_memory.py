"""
SIVI 3.0 — Subconscious Memory
Extracts implicit facts from chat history buffer.
"""

import logging
import threading

logger = logging.getLogger("sivi.subconscious")

class SubconsciousMemory:
    def __init__(self):
        self._buffer = []
        self._lock = threading.Lock()
        
    def log_message(self, role: str, text: str):
        with self._lock:
            self._buffer.append(f"{role}: {text}")
            # Keep buffer bounded — old messages are dropped once we exceed 50
            if len(self._buffer) > 50:
                self._buffer = self._buffer[-50:]
            
    def _extract_facts(self, transcript: list):
        """Extract implicit facts from conversation. Runs in background thread."""
        try:
            from core.memory_vault import memory_vault
            
            chat_log = "\n".join(transcript)
            # [API QUOTA SAVER] Disabled background LLM memory extraction
            # to avoid burning API quota on implicit fact mining.
            # When re-enabled, use text_llm.complete() synchronously via asyncio.run().
            logger.debug(f"[Subconscious] Buffered {len(transcript)} messages (extraction disabled)")
            return
        except Exception as e:
            logger.debug(f"[Subconscious] error: {e}")

    def get_context(self) -> str:
        # Implicit memory is already saved into memory_vault, 
        # so we can just return a placeholder or rely on memory_vault's own context.
        return ""

subconscious_memory = SubconsciousMemory()
