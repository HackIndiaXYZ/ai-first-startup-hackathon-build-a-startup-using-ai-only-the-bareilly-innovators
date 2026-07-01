import os
import sys
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

# Add backend dir to python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.openrouter_llm import openrouter_llm
from core.agent_orchestrator import orchestrator

async def mock_callback(response: str):
    print(f"\n[Sivi Response] -> {response}\n")

async def test():
    print("Testing OpenRouter LLM direct call...")
    response = await openrouter_llm.complete(
        prompt="How many r's are in the word 'strawberry'?",
        model="google/gemma-4-31b-it:free",
        reasoning={"enabled": True}
    )
    print(f"Direct LLM Test Result: {response}\n")

    print("Testing Orchestrator Routing (Code Agent)...")
    await orchestrator.route_task("analyze code in test_openrouter.py", mock_callback)

    print("Testing Orchestrator Routing (Web Agent)...")
    await orchestrator.route_task("summarize page", mock_callback)

    print("Testing Orchestrator Routing (WhatsApp Agent)...")
    await orchestrator.route_task("draft reply to mom", mock_callback)
    
    # Wait for async tasks to finish
    await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(test())
