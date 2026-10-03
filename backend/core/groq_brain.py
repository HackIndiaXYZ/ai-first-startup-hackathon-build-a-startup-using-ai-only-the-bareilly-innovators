"""
Sivi — Groq LPU Brain (Lightning Fast Intelligence)
===================================================
Handles all background text processing tasks at 30x the speed of Gemini REST.
Used for: self-diagnosis, RAG synthesis, deep research, code analysis, 
and command pre-validation/intent classification.

Powered by Groq's LPU architecture using llama-3.3-70b-versatile.
"""

import os
import logging
import json
import asyncio
from typing import Optional, AsyncIterator
from dotenv import load_dotenv

from groq import AsyncGroq

load_dotenv()

logger = logging.getLogger("sivi.groq_brain")

# Default models
GROQ_PRIMARY_MODEL = "llama-3.3-70b-versatile"
GROQ_FALLBACK_MODEL = "llama-3.1-8b-instant"

class GroqBrain:
    """
    Lightning-fast text processing engine using Groq LPU.
    """
    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY", "").strip()
        self.client = AsyncGroq(api_key=self.api_key) if self.api_key else None
        self.is_available = bool(self.api_key)

    async def complete(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.3,
        model: str = GROQ_PRIMARY_MODEL
    ) -> Optional[str]:
        """
        Standard text completion. Returns None if rate-limited or failed,
        allowing fallback to Gemini REST.
        """
        if not self.is_available:
            return None

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            logger.debug(f"[GroqBrain] Calling {model}...")
            response = await self.client.chat.completions.create(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )
            text = response.choices[0].message.content.strip()
            logger.debug(f"[GroqBrain] OK ({len(text)} chars)")
            return text
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "rate limit" in err_str:
                logger.warning(f"[GroqBrain] Rate limited on {model}, falling back...")
                # If primary is rate limited, try fallback model once
                if model == GROQ_PRIMARY_MODEL:
                    return await self.complete(prompt, system, max_tokens, temperature, GROQ_FALLBACK_MODEL)
            logger.error(f"[GroqBrain] Error: {e}")
            return None

    async def stream_complete(self, prompt: str, system: str = "") -> AsyncIterator[str]:
        """Streaming completion for fast UI updates."""
        if not self.is_available:
            yield ""
            return

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            stream = await self.client.chat.completions.create(
                messages=messages,
                model=GROQ_PRIMARY_MODEL,
                temperature=0.7,
                stream=True
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"[GroqBrain] Stream Error: {e}")
            yield ""

    async def classify_intent(self, user_text: str) -> Optional[str]:
        """
        Fast intent routing for commands the Regex/Trie parser misses.
        Returns a valid [CMD: ...] tag or None.
        """
        system = (
            "You are an intent router for a PC assistant. "
            "Output ONLY a valid [CMD: action parameter] tag if the intent is clear. "
            "If it's just conversational, output NONE."
        )
        prompt = f"User said: '{user_text}'. What is the system command?"
        
        result = await self.complete(prompt, system, max_tokens=50, temperature=0.1, model=GROQ_FALLBACK_MODEL)
        if result and "[CMD:" in result:
            return result
        return None

    async def validate_command(self, cmd_tag: str) -> bool:
        """Sanity check a command before executing it."""
        if not self.is_available:
            return True # Assume valid if Groq is down
            
        system = "Reply YES if this is a safe, valid PC command tag. Reply NO if it looks malformed or extremely dangerous without context."
        prompt = f"Tag: {cmd_tag}"
        
        result = await self.complete(prompt, system, max_tokens=10, temperature=0.0, model=GROQ_FALLBACK_MODEL)
        return result and "yes" in result.lower()

    async def diagnose_error(self, cmd_tag: str, cmd_type: str, error_msg: str) -> Optional[str]:
        """
        Lightning-fast self-diagnosis.
        Returns a corrected [CMD: ...] tag to auto-retry, or None.
        """
        system = (
            "You are Sivi's diagnostic brain. A command failed. "
            "If it's a transient error or syntax issue, output a corrected [CMD: ...] tag to retry. "
            "If it's unfixable (module offline, permission denied, file not found), output EXPLAIN: <1 sentence explanation in Hinglish>."
        )
        prompt = f"Command: {cmd_tag}\nType: {cmd_type}\nError: {error_msg}"
        
        return await self.complete(prompt, system, max_tokens=150, temperature=0.2)

    async def research(self, topic: str) -> str:
        """Replaces OpenRouter deep_research."""
        system = "You are an expert researcher. Provide a highly detailed, deeply accurate, and concise 1-paragraph summary of the requested topic, followed by 3 fascinating bullet points. Output plain text."
        prompt = f"Deeply research this topic: {topic}"
        result = await self.complete(prompt, system, temperature=0.4)
        return result or "[Research unavailable — Groq API limit reached]"

    async def analyze_code(self, code_snippet: str) -> str:
        """Replaces OpenRouter analyze_code."""
        system = "You are a senior principal engineer. Analyze the code, find bugs, and provide the exact fix."
        prompt = f"Analyze this code:\n\n{code_snippet}"
        result = await self.complete(prompt, system, temperature=0.2)
        return result or "[Code analysis unavailable — Groq API limit reached]"


groq_brain = GroqBrain()
