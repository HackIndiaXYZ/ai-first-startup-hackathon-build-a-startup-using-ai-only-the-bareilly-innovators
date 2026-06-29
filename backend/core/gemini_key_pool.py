"""
Sivi — Gemini API Key Pool
==========================
Manages a pool of Gemini API keys to:
  1. Maximize free-tier quota by distributing load across keys
  2. Auto-rotate to next key on 429 / quota exceeded errors
  3. Cool down exhausted keys for QUOTA_COOLDOWN_SECONDS (default 15 min)
  4. Permanently disable invalid keys (401)
  5. Expose per-key stats for the dashboard

.env Convention:
  GEMINI_API_KEY        → primary key (required)
  GEMINI_API_KEY_2      → 2nd Google account key (optional)
  GEMINI_API_KEY_3      → 3rd Google account key (optional)
  ...

Free tier per key: ~60 req/min, 1500 req/day
With 3 keys       : ~180 req/min, 4500 req/day  (all free)
"""

import os
import time
import logging
import threading
from typing import Optional

logger = logging.getLogger("sivi.key_pool")

# How long to suspend a key after a quota error (15 minutes)
QUOTA_COOLDOWN_SECONDS = 900

# Cap to prevent inf-loop when all keys are simultaneously bad
_DISABLED = float("inf")


class _KeyEntry:
    """Single key slot in the pool."""

    __slots__ = ("key", "use_count", "last_error", "cooldown_until", "suffix")

    def __init__(self, key: str) -> None:
        self.key: str = key
        self.use_count: int = 0
        self.last_error: Optional[str] = None
        self.cooldown_until: float = 0.0
        self.suffix: str = f"...{key[-6:]}" if len(key) >= 6 else key

    @property
    def is_available(self) -> bool:
        return time.monotonic() >= self.cooldown_until

    @property
    def cooldown_remaining(self) -> int:
        if self.cooldown_until == _DISABLED:
            return -1  # -1 = permanently disabled
        return max(0, int(self.cooldown_until - time.monotonic()))


class GeminiKeyPool:
    """
    Thread-safe Gemini API key pool.

    Usage (singleton, imported as `from gemini_key_pool import key_pool`):
        key = key_pool.get()          # get best available key
        key_pool.report_quota(key)    # 429 received
        key_pool.report_invalid(key)  # 401 received
        key_pool.stats()              # for dashboard
    """

    def __init__(self) -> None:
        self._entries: list[_KeyEntry] = []
        self._lock = threading.Lock()
        self._load()

    # ── Initialization ────────────────────────────────────────────

    def _load(self) -> None:
        """Read all GEMINI_API_KEY* vars from environment."""
        primary = os.getenv("GEMINI_API_KEY", "").strip()
        if primary:
            self._entries.append(_KeyEntry(primary))

        idx = 2
        while True:
            extra = os.getenv(f"GEMINI_API_KEY_{idx}", "").strip()
            if not extra:
                break
            self._entries.append(_KeyEntry(extra))
            idx += 1

        if not self._entries:
            raise RuntimeError(
                "[KeyPool] No Gemini API key found. "
                "Set GEMINI_API_KEY in backend/.env"
            )

        logger.info(
            f"[KeyPool] Loaded {len(self._entries)} key(s): "
            + ", ".join(e.suffix for e in self._entries)
        )

    # ── Public API ────────────────────────────────────────────────

    def get(self) -> str:
        """
        Return the best available key (lowest use_count, not cooling down).
        If ALL keys are in cooldown, returns the soonest-recovering key
        and logs a warning — the caller will receive a 429 and should retry.
        """
        with self._lock:
            available = [e for e in self._entries if e.is_available]

            if not available:
                # All cooling — pick soonest recovery
                soonest = min(self._entries, key=lambda e: e.cooldown_until)
                logger.warning(
                    f"[KeyPool] All keys cooling. "
                    f"Soonest recovery: {soonest.suffix} "
                    f"in {soonest.cooldown_remaining}s"
                )
                return soonest.key

            # Prefer key with fewest uses (load-balance across keys)
            best = min(available, key=lambda e: e.use_count)
            best.use_count += 1
            logger.debug(
                f"[KeyPool] Assigned {best.suffix} "
                f"(use_count={best.use_count})"
            )
            return best.key

    def report_quota(self, key: str) -> None:
        """Call this when the API returns 429 / RESOURCE_EXHAUSTED."""
        with self._lock:
            entry = self._find(key)
            if entry:
                entry.cooldown_until = time.monotonic() + QUOTA_COOLDOWN_SECONDS
                entry.last_error = "QUOTA_EXCEEDED"
                logger.warning(
                    f"[KeyPool] {entry.suffix} quota exceeded — "
                    f"cooling for {QUOTA_COOLDOWN_SECONDS}s"
                )

    def report_invalid(self, key: str) -> None:
        """Call this when the API returns 401 / UNAUTHENTICATED."""
        with self._lock:
            entry = self._find(key)
            if entry:
                entry.cooldown_until = _DISABLED
                entry.last_error = "INVALID_KEY"
                logger.error(
                    f"[KeyPool] {entry.suffix} is INVALID — "
                    f"disabled permanently. Check your .env"
                )

    def stats(self) -> list[dict]:
        """Return sanitized stats for the /key-pool-status dashboard endpoint."""
        with self._lock:
            return [
                {
                    "key_suffix": e.suffix,
                    "use_count": e.use_count,
                    "status": (
                        "disabled" if e.cooldown_until == _DISABLED
                        else "cooling" if not e.is_available
                        else "active"
                    ),
                    "cooldown_remaining_s": e.cooldown_remaining,
                    "last_error": e.last_error,
                }
                for e in self._entries
            ]

    @property
    def key_count(self) -> int:
        return len(self._entries)

    # ── Internal ──────────────────────────────────────────────────

    def _find(self, key: str) -> Optional[_KeyEntry]:
        for e in self._entries:
            if e.key == key:
                return e
        return None


# ── Module-level singleton ─────────────────────────────────────────
key_pool = GeminiKeyPool()
