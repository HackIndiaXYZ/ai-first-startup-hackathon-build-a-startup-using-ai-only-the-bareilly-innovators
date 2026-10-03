"""
Sivi — Text LLM (Gemini REST with Key Pool)
============================================
Handles all non-voice LLM calls using Gemini REST API + the key pool.

Used by:
  - RAG engine (document Q&A)
  - Background agents (HackerNews, email watch)
  - Self-learning diagnosis
  - Code analysis (DEV_ANALYZE_CODE)
  - Script generation (DEV_GENERATE_CODE)

NOT used for:
  - Real-time voice → that is GeminiLiveClient (WebSocket PCM streaming)

Strategy:
  Try every key in the pool once per request. On 429, the pool
  cools that key and returns the next best. If all keys are
  exhausted simultaneously, waits up to MAX_WAIT_SECONDS then
  returns a graceful error string Gemini can read aloud.
"""

import asyncio
import logging
from typing import Optional

import httpx

from core.gemini_key_pool import key_pool
from core.offline_fallback import offline_fallback
from core.groq_brain import groq_brain

logger = logging.getLogger("sivi.text_llm")

# ── Constants ──────────────────────────────────────────────────────

GEMINI_REST_BASE = (
    "https://generativelanguage.googleapis.com"
    "/v1beta/models/{model}:generateContent"
)

# Default model for text tasks — fast, 1M context, free-tier friendly
DEFAULT_TEXT_MODEL = "gemini-1.5-flash"

# If all keys are cooling, wait this long before returning an error
MAX_WAIT_SECONDS = 10

# httpx timeout for a single REST call
REQUEST_TIMEOUT = 30.0


# ── Main Client ────────────────────────────────────────────────────

class TextLLM:
    """
    Non-voice Gemini REST client with automatic key-pool rotation.

    Example:
        result = await text_llm.complete("Summarise this article: ...")
        result = await text_llm.complete(
            prompt="Explain this error.",
            system="You are a Python expert.",
            max_tokens=512,
        )
    """

    def __init__(self, model: str = DEFAULT_TEXT_MODEL) -> None:
        self.model = model
        self._url = GEMINI_REST_BASE.format(model=model)
        # Reuse a single HTTP client for connection pooling (TLS handshake reuse)
        self._http_client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)

    async def complete(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> str:
        """
        Complete a text prompt via Gemini REST.

        Rotates through all available keys on quota errors.
        Returns a human-readable error string (never raises) so
        Gemini Live can read it aloud to the user.
        """
        # Tier 1: Groq (Lightning Fast)
        groq_result = await groq_brain.complete(prompt, system, max_tokens, temperature)
        if groq_result:
            return groq_result
            
        # Tier 2: Gemini REST
        logger.info("[TextLLM] Groq unavailable/rate-limited, falling back to Gemini REST.")
        tried: set[str] = set()

        while True:
            key = key_pool.get()

            # Detect full cycle — all keys attempted
            if key in tried:
                # All keys exhausted; wait briefly for cooldown
                wait = min(MAX_WAIT_SECONDS, 30)
                logger.warning(
                    f"[TextLLM] All {key_pool.key_count} key(s) exhausted. "
                    f"Waiting {wait}s for cooldown recovery..."
                )
                await asyncio.sleep(wait)
                # One final attempt with whatever comes back
                key = key_pool.get()
                result = await self._call(key, prompt, system, max_tokens, temperature)
                if result is not None:
                    return result
                
                # Attempt Offline Fallback (Ollama)
                logger.warning("[TextLLM] Attempting offline fallback...")
                fallback_resp = offline_fallback.generate_offline_response(prompt, system)
                if fallback_resp:
                    return "[OFFLINE MODE] " + fallback_resp

                return (
                    "[Gemini is temporarily rate-limited on all keys and offline fallback is unavailable. "
                    "Please wait a moment and try again.]"
                )

            tried.add(key)
            result = await self._call(key, prompt, system, max_tokens, temperature)
            if result is not None:
                return result
            # _call returned None → key was quota-reported; loop picks next key

    async def _call(
        self,
        key: str,
        prompt: str,
        system: str,
        max_tokens: int,
        temperature: float,
    ) -> Optional[str]:
        """
        One HTTP call to Gemini REST.
        Returns the response text, or None on recoverable errors
        (429, 401) so the caller can rotate to the next key.
        Raises nothing — all errors are logged and return None.
        """
        payload: dict = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        url = f"{self._url}?key={key}"

        try:
            resp = await self._http_client.post(url, json=payload)

            if resp.status_code == 429:
                key_pool.report_quota(key)
                return None  # Caller rotates to next key

            if resp.status_code in (401, 403, 1008):
                key_pool.report_invalid(key)
                return None  # Caller rotates to next key

            if resp.status_code != 200:
                logger.warning(
                    f"[TextLLM] Unexpected status {resp.status_code} "
                    f"from key {key[-6:]}: {resp.text[:200]}"
                )
                return None

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                logger.warning(f"[TextLLM] Empty candidates in response: {data}")
                return "[No response generated]"

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                return "[Empty response content]"

            text = parts[0].get("text", "").strip()
            logger.debug(f"[TextLLM] OK via key ...{key[-6:]} ({len(text)} chars)")
            return text

        except httpx.TimeoutException:
            logger.warning(f"[TextLLM] Timeout on key ...{key[-6:]}")
            return None
        except Exception as exc:
            logger.error(f"[TextLLM] Unexpected error: {exc}")
            return None


# ── Module-level singleton ─────────────────────────────────────────
text_llm = TextLLM()
