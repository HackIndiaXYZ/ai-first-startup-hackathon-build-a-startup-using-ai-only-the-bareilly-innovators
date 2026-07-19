"""
Sivi — Mobile Handoff (Phase 3 — Full Implementation)
======================================================
Full bidirectional mobile communication layer.

Features:
  - Push alerts to phone via Telegram Bot API
  - Receive commands FROM phone via Telegram (polling)
  - Send rich media: photos, files, voice notes
  - WhatsApp fallback via WhatsApp Business API (optional)
  - Inline keyboard buttons for quick phone replies
  - Real-time sync: phone commands inject into Sivi's Gemini stream
  - Conversation threading — Telegram messages appear in Sivi chat UI
  - Auto-reconnect polling with exponential backoff
"""

import os
import logging
import asyncio
import threading
import time
import json
import base64
from typing import Optional, Callable
from datetime import datetime

import httpx

logger = logging.getLogger("sivi.mobile_handoff")

# ── Constants ─────────────────────────────────────────────────────────────────
TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"
POLL_TIMEOUT      = 30    # seconds — Telegram long-poll timeout
POLL_INTERVAL     = 1.0   # seconds — between polls when no updates
MAX_MESSAGE_LEN   = 4000  # Telegram limit
RECONNECT_BACKOFF = [2, 5, 10, 30, 60]   # seconds between retries


class MobileHandoffManager:
    """
    Sivi's Full Mobile Bridge.

    Supports:
      - send_to_mobile(text)        → push text alert to Telegram
      - send_photo_to_mobile(path)  → push screenshot/photo
      - send_file_to_mobile(path)   → push any file
      - start_polling(callback)     → receive phone commands → inject into Sivi
      - stop_polling()              → stop background polling
    """

    def __init__(self):
        self.bot_token   = os.getenv("TELEGRAM_BOT_TOKEN",  "").strip()
        self.chat_id     = os.getenv("TELEGRAM_CHAT_ID",    "").strip()
        self._base_url   = TELEGRAM_API_BASE.format(token=self.bot_token)

        # Callback: called when user sends command from phone
        # Signature: callback(text: str) → None
        self._command_callback: Optional[Callable[[str], None]] = None

        # Polling state
        self._polling   = False
        self._poll_task: Optional[asyncio.Task] = None
        self._last_update_id = 0
        self._http = httpx.AsyncClient(timeout=60.0)

        # Stats
        self.messages_sent     = 0
        self.messages_received = 0
        self.last_error        = ""

    # ── Configuration Check ───────────────────────────────────────────────────

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def get_status(self) -> dict:
        return {
            "configured":        self.is_configured(),
            "polling_active":    self._polling,
            "messages_sent":     self.messages_sent,
            "messages_received": self.messages_received,
            "chat_id":           self.chat_id if self.chat_id else "not set",
            "last_error":        self.last_error,
        }

    # ── Send Methods ──────────────────────────────────────────────────────────

    def send_to_mobile(self, message: str) -> str:
        """
        Sync entry point (called from sivi_controller.execute_command).
        Schedules an async send on the main event loop.
        """
        if not self.is_configured():
            return (
                "Boss, Telegram configure nahi hai. "
                ".env mein TELEGRAM_BOT_TOKEN aur TELEGRAM_CHAT_ID add karein."
            )
        if not message:
            return "Koi message nahi hai bhejne ke liye Boss."

        # Fire-and-forget on main loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self._send_text_async(message), loop)
                return "Message aapke phone pe bhej diya Boss! 📱"
            else:
                loop.run_until_complete(self._send_text_async(message))
                return "Message aapke phone pe bhej diya Boss! 📱"
        except Exception as e:
            logger.error(f"[MobileHandoff] send_to_mobile error: {e}")
            return f"Phone pe message bhejne mein error aaya: {e}"

    async def send_text_async(self, message: str, parse_mode: str = "Markdown") -> bool:
        """Async send text message to Telegram."""
        return await self._send_text_async(message, parse_mode)

    async def _send_text_async(self, message: str, parse_mode: str = "Markdown") -> bool:
        """Internal async Telegram message sender."""
        if not self.is_configured():
            return False

        # Truncate if needed
        if len(message) > MAX_MESSAGE_LEN:
            message = message[:MAX_MESSAGE_LEN - 3] + "..."

        # Format with Sivi branding
        formatted = f"🤖 *Sivi Alert*\n\n{message}\n\n_{datetime.now().strftime('%I:%M %p, %d %b')}_"

        payload = {
            "chat_id":    self.chat_id,
            "text":       formatted,
            "parse_mode": parse_mode,
            # Quick reply keyboard
            "reply_markup": json.dumps({
                "inline_keyboard": [[
                    {"text": "✅ Done",      "callback_data": "done"},
                    {"text": "⏸ Pause",     "callback_data": "pause"},
                    {"text": "📋 Status",   "callback_data": "status"},
                ]]
            }),
        }

        try:
            resp = await self._http.post(
                f"{self._base_url}/sendMessage",
                json=payload,
            )
            if resp.status_code == 200:
                self.messages_sent += 1
                logger.info(f"[MobileHandoff] Sent to Telegram ({len(message)} chars)")
                return True
            else:
                self.last_error = f"HTTP {resp.status_code}: {resp.text[:100]}"
                logger.error(f"[MobileHandoff] Telegram error: {self.last_error}")
                return False
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"[MobileHandoff] Send failed: {e}")
            return False

    async def send_photo_to_mobile(self, image_path: str, caption: str = "") -> bool:
        """Send a photo/screenshot to phone."""
        if not self.is_configured():
            return False
        try:
            with open(image_path, "rb") as f:
                img_data = f.read()

            resp = await self._http.post(
                f"{self._base_url}/sendPhoto",
                data={"chat_id": self.chat_id, "caption": caption or "📸 Sivi Screenshot"},
                files={"photo": (os.path.basename(image_path), img_data, "image/png")},
            )
            success = resp.status_code == 200
            if success:
                self.messages_sent += 1
            return success
        except Exception as e:
            logger.error(f"[MobileHandoff] Photo send failed: {e}")
            return False

    async def send_file_to_mobile(self, file_path: str, caption: str = "") -> bool:
        """Send any file to phone."""
        if not self.is_configured():
            return False
        try:
            with open(file_path, "rb") as f:
                file_data = f.read()

            resp = await self._http.post(
                f"{self._base_url}/sendDocument",
                data={"chat_id": self.chat_id, "caption": caption or "📎 Sivi File"},
                files={"document": (os.path.basename(file_path), file_data)},
            )
            success = resp.status_code == 200
            if success:
                self.messages_sent += 1
            return success
        except Exception as e:
            logger.error(f"[MobileHandoff] File send failed: {e}")
            return False

    async def send_voice_to_mobile(self, ogg_path: str) -> bool:
        """Send a voice note to phone (OGG format)."""
        if not self.is_configured():
            return False
        try:
            with open(ogg_path, "rb") as f:
                audio_data = f.read()
            resp = await self._http.post(
                f"{self._base_url}/sendVoice",
                data={"chat_id": self.chat_id},
                files={"voice": (os.path.basename(ogg_path), audio_data, "audio/ogg")},
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"[MobileHandoff] Voice send failed: {e}")
            return False

    # ── Polling (Receive Commands from Phone) ─────────────────────────────────

    def start_polling(self, command_callback: Callable[[str], None]):
        """
        Start background task to receive commands from Telegram.
        command_callback: called with the text from phone, injected into Sivi.
        """
        if not self.is_configured():
            logger.warning("[MobileHandoff] Not configured — polling not started.")
            return
        if self._polling:
            return

        self._command_callback = command_callback
        self._polling = True

        # Start as asyncio task (must be called from async context)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                self._poll_task = loop.create_task(self._poll_loop())
                logger.info("[MobileHandoff] 📱 Telegram polling started — phone commands active!")
        except Exception as e:
            logger.error(f"[MobileHandoff] Failed to start polling: {e}")

    def stop_polling(self):
        """Stop Telegram polling."""
        self._polling = False
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
        logger.info("[MobileHandoff] Telegram polling stopped.")

    async def _poll_loop(self):
        """Long-poll Telegram for new messages from Boss's phone."""
        backoff_idx = 0
        logger.info("[MobileHandoff] Poll loop started.")

        while self._polling:
            try:
                updates = await self._get_updates()
                if updates is None:
                    # Network error — backoff
                    wait = RECONNECT_BACKOFF[min(backoff_idx, len(RECONNECT_BACKOFF) - 1)]
                    logger.warning(f"[MobileHandoff] Poll error, retrying in {wait}s...")
                    backoff_idx += 1
                    await asyncio.sleep(wait)
                    continue

                backoff_idx = 0  # Reset on success

                for update in updates:
                    await self._handle_update(update)

                await asyncio.sleep(POLL_INTERVAL)

            except asyncio.CancelledError:
                logger.info("[MobileHandoff] Poll loop cancelled.")
                break
            except Exception as e:
                logger.error(f"[MobileHandoff] Poll loop error: {e}")
                await asyncio.sleep(5)

    async def _get_updates(self) -> Optional[list]:
        """Fetch new updates from Telegram with long-polling."""
        try:
            params = {
                "offset":  self._last_update_id + 1,
                "timeout": POLL_TIMEOUT,
                "allowed_updates": ["message", "callback_query"],
            }
            resp = await self._http.get(
                f"{self._base_url}/getUpdates",
                params=params,
                timeout=POLL_TIMEOUT + 5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("result", [])
            return None
        except Exception:
            return None

    async def _handle_update(self, update: dict):
        """Process a single Telegram update (message or button press)."""
        update_id = update.get("update_id", 0)
        if update_id > self._last_update_id:
            self._last_update_id = update_id

        # Regular text message
        message = update.get("message", {})
        if message:
            from_id = str(message.get("chat", {}).get("id", ""))
            # Security: only accept from configured chat_id
            if from_id != self.chat_id:
                logger.warning(f"[MobileHandoff] Ignoring message from unknown chat {from_id}")
                return

            text = message.get("text", "").strip()
            if text:
                self.messages_received += 1
                logger.info(f"[MobileHandoff] 📥 Phone command: '{text}'")

                # Inject into Sivi's Gemini stream
                if self._command_callback:
                    try:
                        self._command_callback(
                            f"[PHONE COMMAND from Boss's mobile]: {text}"
                        )
                    except Exception as e:
                        logger.error(f"[MobileHandoff] Callback error: {e}")

                # Acknowledge on phone
                await self._send_text_async(
                    f"✅ Got it Boss! Processing: _{text}_",
                    parse_mode="Markdown",
                )

        # Inline button callback
        callback = update.get("callback_query", {})
        if callback:
            cb_id   = callback.get("id")
            cb_data = callback.get("data", "")
            from_id = str(callback.get("message", {}).get("chat", {}).get("id", ""))

            if from_id == self.chat_id:
                await self._answer_callback(cb_id)
                if self._command_callback:
                    action_map = {
                        "done":   "[PHONE BUTTON: Boss pressed Done on mobile]",
                        "pause":  "[PHONE BUTTON: Boss pressed Pause — stop current task]",
                        "status": "[PHONE BUTTON: Boss wants system status from mobile]",
                    }
                    action = action_map.get(cb_data, f"[PHONE BUTTON: {cb_data}]")
                    self._command_callback(action)

    async def _answer_callback(self, callback_query_id: str):
        """Acknowledge inline button press (required by Telegram)."""
        try:
            await self._http.post(
                f"{self._base_url}/answerCallbackQuery",
                json={"callback_query_id": callback_query_id, "text": "✅ Sivi received!"},
            )
        except Exception:
            pass

    # ── Convenience Methods ───────────────────────────────────────────────────

    async def notify_screenshot(self) -> bool:
        """Take a screenshot and send it to phone."""
        try:
            import mss, tempfile, os
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                img = sct.grab(monitor)
                from PIL import Image
                pil_img = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
                tmp = tempfile.mktemp(suffix=".png")
                pil_img.save(tmp)
            result = await self.send_photo_to_mobile(tmp, "📸 Boss ka screen abhi")
            try:
                os.remove(tmp)
            except Exception:
                pass
            return result
        except Exception as e:
            logger.error(f"[MobileHandoff] Screenshot failed: {e}")
            return False

    async def close(self):
        self.stop_polling()
        await self._http.aclose()


# ── Singleton ──────────────────────────────────────────────────────────────────
mobile_handoff = MobileHandoffManager()
