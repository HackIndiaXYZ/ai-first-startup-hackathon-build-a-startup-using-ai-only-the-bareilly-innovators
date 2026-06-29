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
        # If it's a RAG query
        if "document" in command.lower() or "read my files" in command.lower() or "rag" in command.lower():
            logger.info("Routing to RAG Engine...")
            asyncio.create_task(self._run_rag_agent(command, send_response_callback))
            return True
            
        # If it's code analysis
        if "analyze code" in command.lower() or "debug this" in command.lower():
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
