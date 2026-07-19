"""
Sivi — Offline Fallback Brain (Phase 2 — Full Implementation)
=============================================================
Connects to local Ollama instance (Llama 3.1 8B or any available model).
Provides full offline capability when Gemini API is unavailable.

Features:
  - Auto-detects Ollama and best available model
  - Streaming support for faster response
  - Sivi personality preserved even offline
  - Network status monitor with auto-recovery
  - Async-first design matching text_llm.py interface
  - Falls back gracefully through multiple tiers:
    Tier 1: Gemini API (online)
    Tier 2: Ollama local LLM (offline)
    Tier 3: Rule-based deterministic responses (no LLM at all)
"""

import logging
import asyncio
import time
import json
import threading
from typing import Optional
from datetime import datetime

import httpx

logger = logging.getLogger("sivi.offline_fallback")

# ── Constants ─────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL   = "http://localhost:11434"
PREFERRED_MODELS  = ["llama3.1:8b", "llama3.1", "llama3:8b", "llama3", "mistral", "phi3", "gemma2"]
OLLAMA_TIMEOUT    = 60.0   # seconds — local LLM can be slow first run
PING_TIMEOUT      = 2.0    # seconds — availability check
NETWORK_CHECK_URL = "https://dns.google"  # lightweight network probe

# ── Tier-3 Deterministic Responses (zero dependency) ─────────────────────────
_DETERMINISTIC = {
    "time":    lambda: f"Abhi {datetime.now().strftime('%I:%M %p')} baj rahe hain Boss.",
    "date":    lambda: f"Aaj {datetime.now().strftime('%d %B %Y')} hai Boss.",
    "hello":   lambda: "Hello Boss! Main offline mode mein hoon, lekin aapke liye yahaan hoon.",
    "hi":      lambda: "Hi Boss! Offline hoon lekin ready hoon.",
    "help":    lambda: "Boss, abhi main offline mode mein hoon. Basic commands jaise time, date, volume, apps khol/band kar sakti hoon.",
    "offline": lambda: "Haan Boss, Gemini se connection nahi hai abhi. Local brain se kaam chal raha hai.",
}


class NetworkMonitor:
    """
    Lightweight background monitor that tracks internet + Ollama availability.
    Exposes simple boolean flags for other modules to query without blocking.
    """

    def __init__(self):
        self.internet_available: bool = True
        self.ollama_available:   bool = False
        self._best_model:        str  = ""
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Start background monitoring thread (daemon)."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True, name="sivi.net_monitor")
        self._thread.start()
        logger.info("[NetMonitor] Started background network monitoring.")

    def stop(self):
        self._stop_event.set()

    @property
    def best_model(self) -> str:
        with self._lock:
            return self._best_model

    def _check_internet(self) -> bool:
        try:
            import urllib.request
            urllib.request.urlopen(NETWORK_CHECK_URL, timeout=3)
            return True
        except Exception:
            return False

    def _check_ollama(self) -> tuple[bool, str]:
        """Returns (available, best_model_name)."""
        try:
            resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=PING_TIMEOUT)
            if resp.status_code == 200:
                models = [m.get("name", "") for m in resp.json().get("models", [])]
                if models:
                    # Pick best model by preference
                    for pref in PREFERRED_MODELS:
                        for m in models:
                            if pref.lower() in m.lower():
                                return True, m
                    return True, models[0]  # any model
                return True, ""  # ollama running but no model pulled
        except Exception:
            pass
        return False, ""

    def _monitor_loop(self):
        while not self._stop_event.is_set():
            internet = self._check_internet()
            ollama_ok, model = self._check_ollama()

            with self._lock:
                prev_internet = self.internet_available
                self.internet_available = internet
                self.ollama_available   = ollama_ok
                self._best_model        = model

            # Log state transitions
            if prev_internet != internet:
                if internet:
                    logger.info("[NetMonitor] 🌐 Internet restored — switching back to Gemini.")
                else:
                    logger.warning("[NetMonitor] ⚠️  Internet lost — Sivi switching to offline mode.")

            # Check every 15 seconds
            self._stop_event.wait(15.0)


class OfflineFallbackManager:
    """
    Sivi's Offline Fallback Brain — Full Phase 2 Implementation.

    Usage:
        # Check if we should use offline mode
        if not offline_fallback.is_online():
            response = await offline_fallback.complete(prompt, system)

        # Or let it decide automatically
        response = await offline_fallback.smart_complete(prompt, system)
    """

    def __init__(self):
        self._http = httpx.AsyncClient(timeout=OLLAMA_TIMEOUT)
        self._net  = NetworkMonitor()
        self._net.start()

        # Sivi's offline personality prompt (condensed version)
        self._offline_system = (
            "You are Sivi, a warm, caring AI assistant. "
            "You speak in Hinglish (Hindi + English mix). "
            "You are currently running in OFFLINE mode using a local LLM. "
            "Be honest that you are offline but stay warm, helpful, and confident. "
            "Keep responses short (1-3 sentences). "
            "Always address the user as 'Boss'. "
            "NEVER say you are Llama or any other model — you are always Sivi."
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    def is_online(self) -> bool:
        """True if internet + Gemini should be reachable."""
        return self._net.internet_available

    def is_ollama_ready(self) -> bool:
        """True if local Ollama is running with a model."""
        return self._net.ollama_available and bool(self._net.best_model)

    def get_status(self) -> dict:
        """Status dict for dashboard /offline-status endpoint."""
        return {
            "internet":       self._net.internet_available,
            "ollama_running": self._net.ollama_available,
            "best_model":     self._net.best_model,
            "tier": (
                "online"       if self._net.internet_available  else
                "ollama"       if self.is_ollama_ready()        else
                "deterministic"
            ),
        }

    async def complete(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 512,
    ) -> str:
        """
        Generate a response using the best available offline method.

        Priority:
          1. Ollama local LLM (if running)
          2. Deterministic rule-based answer
          3. Graceful error message
        """
        # Tier 1 — try Ollama
        if self.is_ollama_ready():
            result = await self._ollama_complete(prompt, system, max_tokens)
            if result:
                return result
            logger.warning("[Offline] Ollama call failed, falling back to deterministic.")

        # Tier 2 — deterministic rules
        deterministic = self._try_deterministic(prompt)
        if deterministic:
            return deterministic

        # Tier 3 — graceful failure
        return (
            "Boss, abhi main completely offline hoon aur local AI bhi available nahi hai. "
            "Please internet check karein ya Ollama install karein."
        )

    # Backward-compatible sync wrapper (used by text_llm.py fallback path)
    def generate_offline_response(self, prompt: str, system: str = "") -> Optional[str]:
        """
        Sync wrapper for generate_offline_response() — backwards compat with text_llm.py.
        Runs the async complete() in a new event loop if needed.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're inside an async context — use threadsafe approach
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self.complete(prompt, system))
                    return future.result(timeout=OLLAMA_TIMEOUT)
            else:
                return loop.run_until_complete(self.complete(prompt, system))
        except Exception as e:
            logger.error(f"[Offline] generate_offline_response error: {e}")
            return None

    def is_ollama_available(self) -> bool:
        """Backward compat alias."""
        return self._net.ollama_available

    def get_available_models(self) -> list:
        """Backward compat — returns list of model names."""
        try:
            resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=PING_TIMEOUT)
            if resp.status_code == 200:
                return [m.get("name", "") for m in resp.json().get("models", [])]
        except Exception:
            pass
        return []

    # ── Private Methods ────────────────────────────────────────────────────────

    async def _ollama_complete(self, prompt: str, system: str, max_tokens: int) -> Optional[str]:
        """Call Ollama /api/chat endpoint (chat format — better than /api/generate)."""
        model = self._net.best_model
        if not model:
            return None

        # Use effective system: caller's system OR Sivi's offline personality
        effective_system = system if system else self._offline_system

        payload = {
            "model":  model,
            "stream": False,
            "messages": [
                {"role": "system",  "content": effective_system},
                {"role": "user",    "content": prompt},
            ],
            "options": {
                "temperature":  0.5,
                "num_predict":  max_tokens,
                "top_p":        0.9,
            },
        }

        try:
            logger.info(f"[Offline] Calling Ollama model: {model}")
            start = time.monotonic()
            resp = await self._http.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload,
            )

            if resp.status_code == 200:
                data = resp.json()
                text = data.get("message", {}).get("content", "").strip()
                elapsed = time.monotonic() - start
                logger.info(f"[Offline] Ollama response in {elapsed:.1f}s ({len(text)} chars)")
                return text if text else None
            else:
                logger.error(f"[Offline] Ollama error {resp.status_code}: {resp.text[:200]}")
                return None

        except httpx.TimeoutException:
            logger.warning(f"[Offline] Ollama timeout after {OLLAMA_TIMEOUT}s")
            return None
        except Exception as e:
            logger.error(f"[Offline] Ollama exception: {e}")
            return None

    def _try_deterministic(self, prompt: str) -> Optional[str]:
        """Rule-based instant answers for common queries — zero LLM dependency."""
        pl = prompt.lower()
        for key, fn in _DETERMINISTIC.items():
            if key in pl:
                return fn()
        return None

    async def close(self):
        """Cleanup."""
        self._net.stop()
        await self._http.aclose()


# ── Singleton ──────────────────────────────────────────────────────────────────
offline_fallback = OfflineFallbackManager()
