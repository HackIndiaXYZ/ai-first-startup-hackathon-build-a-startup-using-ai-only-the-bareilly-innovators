"""
SIVI AI — GenAI Runner (Key Pool Wrapper for google.genai SDK)
==============================================================
Wraps `google.genai` Client calls to automatically rotate
API keys using the `gemini_key_pool` when encountering rate limits
(429) or invalid/forbidden errors (401, 403).
"""

import time
import logging
from typing import Callable, Any

try:
    from google import genai
    from google.genai.errors import APIError
    _genai_available = True
except ImportError:
    genai = None
    APIError = Exception
    _genai_available = False

from core.gemini_key_pool import key_pool

logger = logging.getLogger("sivi.genai_runner")
MAX_WAIT_SECONDS = 10

def run_with_key_pool(func: Callable) -> Any:
    """
    Executes `func(client)` using the google-genai SDK, automatically 
    rotating through available API keys in the key_pool if it hits 429 or 403.
    
    `func` must be a synchronous callable that takes a single argument `client` 
    (which is an instance of `google.genai.Client`).
    """
    if not _genai_available:
        logger.error("[GenAI Runner] google.genai package is not installed.")
        return None

    tried = set()

    while True:
        key = key_pool.get()

        # If we have tried all keys in this cycle, wait and try one last time.
        if key in tried:
            wait = min(MAX_WAIT_SECONDS, 30)
            logger.warning(
                f"[GenAI Runner] All {key_pool.key_count} key(s) exhausted. "
                f"Waiting {wait}s for cooldown recovery..."
            )
            time.sleep(wait)
            key = key_pool.get()
            tried.add(key)  # FIX: prevent infinite loop if all keys permanently disabled
            client = genai.Client(api_key=key)
            try:
                return func(client)
            except Exception as e:
                logger.error(f"[GenAI Runner] Final retry failed: {e}")
                return None
                
        tried.add(key)
        client = genai.Client(api_key=key)
        
        try:
            return func(client)
        except APIError as e:
            code = getattr(e, "code", getattr(e, "status", None))
            
            if code == 429:
                key_pool.report_quota(key)
                continue # Retry with next key
            elif code in (401, 403, 1008):
                key_pool.report_invalid(key)
                continue # Retry with next key
            else:
                logger.warning(f"[GenAI Runner] Unexpected APIError {code} from key {key[-6:]}: {e}")
                return None
        except Exception as e:
            logger.error(f"[GenAI Runner] Unexpected error: {e}")
            return None
