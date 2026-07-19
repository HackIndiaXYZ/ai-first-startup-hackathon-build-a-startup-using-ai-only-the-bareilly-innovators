"""
Sivi — Agent Orchestrator
Sits between the Command Parser and the execution layer.
Delegates complex or ambiguous tasks to background LLM agents (TextLLM)
so that real-time system control isn't blocked.
"""

import asyncio
import logging
from core.text_llm import text_llm
from core.rag_engine import rag_engine

logger = logging.getLogger("sivi.agent_orchestrator")

class AgentOrchestrator:
    def __init__(self):
        pass

    async def route_task(self, command: str, send_response_callback):
        """
        Evaluate if a task is complex (research, coding, RAG) or simple.
        If complex, run in background and use the callback to speak the result.
        """
        cmd_lower = command.lower()
        
        # RAG queries — use specific phrases to avoid false positives
        # ("I documented the bug" should NOT route to RAG)
        rag_triggers = [
            "search my documents", "read my files", "search my files",
            "find in documents", "query documents", "rag search",
            "look in my documents", "what do my documents say",
        ]
        if any(trigger in cmd_lower for trigger in rag_triggers):
            logger.info("Routing to RAG Engine...")
            asyncio.create_task(self._run_rag_agent(command, send_response_callback))
            return True
            
        # Code analysis — use specific phrases
        code_triggers = [
            "analyze this code", "debug this code", "review this code",
            "find bugs in this code", "explain this code",
        ]
        if any(trigger in cmd_lower for trigger in code_triggers):
            logger.info("Routing to Code Agent...")
            asyncio.create_task(self._run_code_agent(command, send_response_callback))
            return True

        return False # Not a complex task, let normal command parser handle it

    async def _run_rag_agent(self, command, callback):
        result = await rag_engine.answer_question(command)
        if callback:
            await callback(result)

    async def _run_code_agent(self, command, callback):
        # In a real scenario, this would read the filesystem
        prompt = f"User wants help with coding: {command}. Provide a concise 1-2 sentence summary of what needs to be done."
        result = await text_llm.complete(prompt=prompt, system="You are Sivi, an expert coder.")
        if callback:
            await callback(result)

orchestrator = AgentOrchestrator()
