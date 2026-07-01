"""
SIVI 3.0 — Subconscious Memory
Extracts implicit facts from chat history buffer.
"""

import logging
import asyncio

logger = logging.getLogger("sivi.subconscious")

class SubconsciousMemory:
    def __init__(self):
        self._buffer = []
        
    def log_message(self, role: str, text: str):
        self._buffer.append(f"{role}: {text}")
        if len(self._buffer) > 20:
            # Process in background
            asyncio.create_task(self._extract_facts(list(self._buffer)))
            self._buffer.clear()
            
    async def _extract_facts(self, transcript: list):
        try:
            from core.text_llm import text_llm
            from core.memory_vault import memory_vault
            
            chat_log = "\n".join(transcript)
            prompt = f"Analyze this conversation. Extract ONLY persistent factual preferences or habits about the user (e.g., likes dark mode, hates spicy food, works late). Return as a list of bullet points. If nothing significant, return 'NONE'.\n{chat_log}"
            
            result = await text_llm.complete(prompt=prompt, system="You are the Subconscious. Extract implicit facts.")
            if "NONE" not in result and result.strip():
                for line in result.split("\n"):
                    fact = line.strip("-* ")
                    if fact:
                        memory_vault.remember(fact)
                        logger.info(f"[Subconscious] Extracted implicit fact: {fact}")
        except Exception as e:
            logger.debug(f"[Subconscious] error: {e}")

    def get_context(self) -> str:
        # Implicit memory is already saved into memory_vault, 
        # so we can just return a placeholder or rely on memory_vault's own context.
        return ""

subconscious_memory = SubconsciousMemory()
