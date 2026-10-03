"""
Sivi — OpenRouter LLM 
======================
Handles ultra-advanced "Deep Research" and "Code Analysis" tasks using 
OpenAI's models (gpt-4o, o3-mini) via the OpenRouter API.

Used by:
  - AgentOrchestrator for complex reasoning.
"""

import os
import json
import logging
import httpx
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("sivi.openrouter_llm")

class OpenRouterLLM:
    def __init__(self):
        self.api_key = os.environ.get("OPENROUTER_API_KEY", "")
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self._http = httpx.AsyncClient(timeout=60.0) # Reasoning models can take a while

    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://sivi.ai",
            "X-Title": "Sivi AI Desktop",
            "Content-Type": "application/json"
        }

    async def complete(self, prompt: str, system: str = "", model: str = "openai/gpt-4o-mini", max_tokens: int = 2000) -> Optional[str]:
        if not self.api_key:
            return "[OpenRouter API Key not configured.]"

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
        }
        
        # OpenRouter/OpenAI specific params
        if "o1" not in model and "o3" not in model:
            payload["max_tokens"] = max_tokens

        try:
            resp = await self._http.post(self.base_url, headers=self._get_headers(), json=payload)
            
            if resp.status_code != 200:
                logger.error(f"[OpenRouter] API Error {resp.status_code}: {resp.text}")
                return f"[OpenRouter API Error: {resp.status_code}]"

            data = resp.json()
            return data["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"[OpenRouter] Failed: {e}")
            return f"[Failed to reach OpenRouter: {e}]"

    async def deep_research(self, topic: str) -> str:
        """Uses a highly capable model to synthesize deep research on a topic."""
        system = "You are an expert researcher. Provide a highly detailed, deeply accurate, and concise 1-paragraph summary of the requested topic, followed by 3 fascinating bullet points. Output plain text (no markdown headings, just paragraphs and bullet points)."
        prompt = f"Deeply research this topic: {topic}"
        # Using Llama-3.3-70B Instruct (Free on OpenRouter) for deep reasoning/research
        return await self.complete(prompt, system=system, model="meta-llama/llama-3.3-70b-instruct:free")

    async def analyze_code(self, code_snippet: str) -> str:
        """Uses reasoning model for code bugs."""
        system = "You are a senior principal engineer. Analyze the code, find bugs, and provide the exact fix."
        prompt = f"Analyze this code:\n\n{code_snippet}"
        # Using gpt-4o-mini which has been verified to work with the current key
        return await self.complete(prompt, system=system, model="openai/gpt-4o-mini")

    async def patch_code(self, file_content: str, instruction: str) -> str:
        """Returns SEARCH/REPLACE blocks to intelligently modify a file without rewriting it fully."""
        system = (
            "You are an expert autonomous SWE. The user wants to modify a file. "
            "Output ONLY one or more SEARCH/REPLACE blocks in the exact format below, and nothing else.\n"
            "<<<<\n"
            "exact old lines to be replaced (must match exactly)\n"
            "====\n"
            "new lines to replace them with\n"
            ">>>>\n"
            "Do not include markdown ticks around the block."
        )
        prompt = f"Instruction: {instruction}\n\nFile Content:\n{file_content}"
        return await self.complete(prompt, system=system, model="openai/gpt-4o-mini", max_tokens=4000)

openrouter_llm = OpenRouterLLM()
