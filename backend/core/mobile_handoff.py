"""
Sivi — Mobile Handoff (Advanced Implementation)
======================================================
Full bidirectional mobile communication layer via Telegram Bot API.

Features:
  - Push alerts to phone via Telegram with rich context menus
  - Receive commands FROM phone via Telegram (polling) with persist offset
  - Send rich media: photos, files, voice notes
  - Receive rich media: process phone images (Gemini Vision) and voice notes
  - Two-way queue: offline command queue (phone->PC) and retry queue (PC->phone)
  - Smart bypass: simple PC commands instantly execute without Gemini roundtrip
  - Interactive /menu for PC control grid on phone
"""

import os
import logging
import asyncio
import time
import json
import base64
import tempfile
from typing import Optional, Callable
from collections import deque
from datetime import datetime

import httpx

logger = logging.getLogger("sivi.mobile_handoff")

# ── Constants ─────────────────────────────────────────────────────────────────
TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"
POLL_TIMEOUT      = 30    # seconds — Telegram long-poll timeout
POLL_INTERVAL     = 1.0   # seconds — between polls when no updates
MAX_MESSAGE_LEN   = 4000  # Telegram limit
RECONNECT_BACKOFF = [2, 5, 10, 30, 60]   # seconds between retries

# Data files
OFFSET_FILE = os.path.expanduser("~/.sivi_telegram_offset.json")
MEDIA_CACHE_DIR = os.path.expanduser("~/.sivi_mobile_media")
os.makedirs(MEDIA_CACHE_DIR, exist_ok=True)

# ── Button Sets ───────────────────────────────────────────────────────────────
BUTTON_SETS = {
    "timer": [
        [{"text": "⏳ Snooze 5m", "callback_data": "cmd:set timer for 5 minutes"}],
        [{"text": "✅ Done", "callback_data": "done"}]
    ],
    "system": [
        [{"text": "💻 System Status", "callback_data": "cmd:system status"}, 
         {"text": "📸 Screenshot", "callback_data": "cmd:take screenshot"}]
    ],
    "file": [
        [{"text": "✅ Done", "callback_data": "done"}]
    ],
    "default": [
        [{"text": "✅ Done", "callback_data": "done"},
         {"text": "📊 Status", "callback_data": "cmd:system status"}]
    ],
    "menu": [
        [{"text": "📸 Screen", "callback_data": "cmd:take screenshot"}, {"text": "🔒 Lock PC", "callback_data": "cmd:lock screen"}, {"text": "💻 Status", "callback_data": "cmd:system status"}],
        [{"text": "🔊 Vol Up", "callback_data": "cmd:volume up"}, {"text": "🔉 Vol Down", "callback_data": "cmd:volume down"}, {"text": "🔇 Mute", "callback_data": "cmd:mute the volume"}],
        [{"text": "☀️ Bright+", "callback_data": "cmd:brightness up"}, {"text": "🌙 Bright-", "callback_data": "cmd:brightness down"}, {"text": "😴 Sleep PC", "callback_data": "cmd:sleep mode"}],
        [{"text": "📋 Clipboard", "callback_data": "cmd:what's on clipboard"}, {"text": "📰 News", "callback_data": "cmd:news"}, {"text": "📅 Calendar", "callback_data": "cmd:calendar"}]
    ]
}


class MobileHandoffManager:
    def __init__(self):
        self.bot_token   = os.getenv("TELEGRAM_BOT_TOKEN",  "").strip()
        self.chat_id     = os.getenv("TELEGRAM_CHAT_ID",    "").strip()
        self._base_url   = TELEGRAM_API_BASE.format(token=self.bot_token)

        self._command_callback: Optional[Callable[[str], None]] = None
        
        # State
        self._polling   = False
        self._poll_task: Optional[asyncio.Task] = None
        self._outbound_worker_task: Optional[asyncio.Task] = None
        self._last_update_id = self._load_offset()
        self._http = httpx.AsyncClient(timeout=60.0)
        
        # Queues
        self._pending_inbound_commands = deque(maxlen=50) # Commands from phone waiting for Gemini
        self._outbound_queue = asyncio.Queue()            # Messages waiting to be sent to phone

        # Stats
        self.messages_sent     = 0
        self.messages_received = 0
        self.last_error        = ""
        self.last_activity     = 0.0

    # ── Configuration & Persist ───────────────────────────────────────────────

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def get_status(self) -> dict:
        return {
            "configured":        self.is_configured(),
            "polling_active":    self._polling,
            "messages_sent":     self.messages_sent,
            "messages_received": self.messages_received,
            "inbound_queue":     len(self._pending_inbound_commands),
            "outbound_queue":    self._outbound_queue.qsize(),
            "chat_id":           self.chat_id if self.chat_id else "not set",
            "last_error":        self.last_error,
            "last_activity_sec": round(time.time() - self.last_activity, 1) if self.last_activity else -1,
        }

    def _load_offset(self) -> int:
        try:
            if os.path.exists(OFFSET_FILE):
                with open(OFFSET_FILE, "r") as f:
                    return json.load(f).get("update_id", 0)
        except Exception:
            pass
        return 0

    def _save_offset(self, update_id: int):
        try:
            with open(OFFSET_FILE, "w") as f:
                json.dump({"update_id": update_id}, f)
        except Exception:
            pass

    # ── Outbound Queue Worker (Retry Logic) ───────────────────────────────────

    async def _outbound_worker(self):
        """Worker that processes outbound messages and retries on failure."""
        logger.info("[MobileHandoff] Outbound worker started.")
        while self._polling:
            try:
                task = await self._outbound_queue.get()
                payload, files, endpoint, retries = task
                
                success = False
                backoff = 2
                
                for attempt in range(retries):
                    try:
                        if files:
                            # Requires multipart form
                            resp = await self._http.post(
                                f"{self._base_url}/{endpoint}",
                                data=payload,
                                files=files,
                                timeout=20.0
                            )
                        else:
                            resp = await self._http.post(
                                f"{self._base_url}/{endpoint}",
                                json=payload,
                                timeout=15.0
                            )
                            
                        if resp.status_code == 200:
                            self.messages_sent += 1
                            self.last_activity = time.time()
                            success = True
                            break
                        else:
                            self.last_error = f"HTTP {resp.status_code}: {resp.text[:100]}"
                            logger.error(f"[MobileHandoff] Send failed: {self.last_error}")
                    except Exception as e:
                        self.last_error = str(e)
                        logger.error(f"[MobileHandoff] Send exception (attempt {attempt+1}/{retries}): {e}")
                        
                    if attempt < retries - 1:
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        
                if not success:
                    logger.warning("[MobileHandoff] Message permanently dropped after retries.")
                    
                self._outbound_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[MobileHandoff] Outbound worker error: {e}")
                await asyncio.sleep(1)

    def _queue_outbound(self, endpoint: str, payload: dict, files=None, retries=3):
        """Queue a request to be sent to Telegram."""
        if not self.is_configured():
            return
        if self._polling:
            self._outbound_queue.put_nowait((payload, files, endpoint, retries))
        else:
            logger.warning("[MobileHandoff] Polling not active, dropping outbound message.")

    # ── Send Methods ──────────────────────────────────────────────────────────

    def send_to_mobile(self, message: str, button_set: str = "default") -> str:
        """Sync entry point to push message."""
        if not self.is_configured():
            return "Telegram missing."
        if not message:
            return "Empty message."
            
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(self.send_text_async(message, parse_mode="Markdown", button_set=button_set), loop)
        else:
            loop.run_until_complete(self.send_text_async(message, parse_mode="Markdown", button_set=button_set))
        return "Message sent to mobile."

    async def send_text_async(self, message: str, parse_mode: str = "Markdown", button_set: str = "default") -> bool:
        if not self.is_configured():
            return False

        if len(message) > MAX_MESSAGE_LEN:
            message = message[:MAX_MESSAGE_LEN - 3] + "..."

        formatted = f"🤖 *Sivi Alert*\n\n{message}\n\n_{datetime.now().strftime('%I:%M %p, %d %b')}_"
        
        buttons = BUTTON_SETS.get(button_set, BUTTON_SETS["default"])
        if button_set == "none":
            reply_markup = None
        else:
            reply_markup = json.dumps({"inline_keyboard": buttons})

        payload = {
            "chat_id":    self.chat_id,
            "text":       formatted,
            "parse_mode": parse_mode,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        self._queue_outbound("sendMessage", payload)
        return True

    async def send_photo_to_mobile(self, image_path: str, caption: str = "") -> bool:
        if not self.is_configured():
            return False
        try:
            with open(image_path, "rb") as f:
                img_data = f.read()
            payload = {"chat_id": self.chat_id, "caption": caption or "📸 Sivi Screenshot"}
            files = {"photo": (os.path.basename(image_path), img_data, "image/png")}
            self._queue_outbound("sendPhoto", payload, files)
            return True
        except Exception as e:
            logger.error(f"[MobileHandoff] Photo read failed: {e}")
            return False

    async def send_file_to_mobile(self, file_path: str, caption: str = "") -> bool:
        if not self.is_configured():
            return False
        try:
            with open(file_path, "rb") as f:
                file_data = f.read()
            payload = {"chat_id": self.chat_id, "caption": caption or "📎 Sivi File"}
            files = {"document": (os.path.basename(file_path), file_data)}
            self._queue_outbound("sendDocument", payload, files)
            return True
        except Exception as e:
            logger.error(f"[MobileHandoff] File read failed: {e}")
            return False

    async def notify_screenshot(self) -> bool:
        try:
            import mss
            from PIL import Image
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                img = sct.grab(monitor)
                pil_img = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
                
                # FIX #4: Use NamedTemporaryFile properly (thread-safe, avoids mktemp deprecation)
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp_path = tmp.name
                    pil_img.save(tmp_path)
                    
            await self.send_photo_to_mobile(tmp_path, "📸 PC Screen")
            
            # Clean up after a short delay since it's queued asynchronously
            async def cleanup(path):
                await asyncio.sleep(10)
                try:
                    os.remove(path)
                except:
                    pass
            asyncio.create_task(cleanup(tmp_path))
            return True
        except Exception as e:
            logger.error(f"[MobileHandoff] Screenshot failed: {e}")
            return False

    # ── Polling & Inbound Command Handling ────────────────────────────────────

    def start_polling(self, command_callback: Callable[[str], None]):
        """Save callback. Requires start_polling_on_loop to be called inside event loop."""
        self._command_callback = command_callback

    def start_polling_on_loop(self):
        """Actually starts the async task (Fixes bug #1 race condition)."""
        if not self.is_configured():
            logger.warning("[MobileHandoff] Not configured — polling not started.")
            return
        if self._polling:
            return

        self._polling = True
        loop = asyncio.get_event_loop()
        self._poll_task = loop.create_task(self._poll_loop())
        self._outbound_worker_task = loop.create_task(self._outbound_worker())
        logger.info("[MobileHandoff] 📱 Telegram polling & outbound queue started.")

    def stop_polling(self):
        self._polling = False
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
        if self._outbound_worker_task and not self._outbound_worker_task.done():
            self._outbound_worker_task.cancel()
        logger.info("[MobileHandoff] Stopped.")

    async def _poll_loop(self):
        backoff_idx = 0
        while self._polling:
            try:
                updates = await self._get_updates()
                if updates is None:
                    wait = RECONNECT_BACKOFF[min(backoff_idx, len(RECONNECT_BACKOFF) - 1)]
                    backoff_idx += 1
                    await asyncio.sleep(wait)
                    continue

                backoff_idx = 0
                for update in updates:
                    await self._handle_update(update)

                await asyncio.sleep(POLL_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[MobileHandoff] Poll loop error: {e}")
                await asyncio.sleep(5)

    async def _get_updates(self) -> Optional[list]:
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

    async def _download_file(self, file_id: str, suffix: str) -> Optional[str]:
        """Download file from Telegram using file_id."""
        try:
            # Get file path
            resp = await self._http.get(f"{self._base_url}/getFile", params={"file_id": file_id})
            if resp.status_code != 200: return None
            
            file_path_rel = resp.json().get("result", {}).get("file_path")
            if not file_path_rel: return None
            
            # Download actual file
            dl_url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path_rel}"
            dl_resp = await self._http.get(dl_url)
            if dl_resp.status_code != 200: return None
            
            with tempfile.NamedTemporaryFile(suffix=suffix, dir=MEDIA_CACHE_DIR, delete=False) as tmp:
                tmp.write(dl_resp.content)
                return tmp.name
        except Exception as e:
            logger.error(f"[MobileHandoff] Download failed: {e}")
            return None

    async def _handle_update(self, update: dict):
        update_id = update.get("update_id", 0)
        if update_id > self._last_update_id:
            self._last_update_id = update_id
            self._save_offset(update_id)

        self.last_activity = time.time()

        # Regular Message
        message = update.get("message", {})
        if message:
            from_id = str(message.get("chat", {}).get("id", ""))
            if from_id != self.chat_id: return
            self.messages_received += 1

            # Text Message
            text = message.get("text", "").strip()
            
            # PC Control Menu
            if text.lower() == "/menu":
                await self.send_text_async("🎛 **PC Control Menu**", button_set="menu")
                return

            if text:
                logger.info(f"[MobileHandoff] 📥 Phone cmd: '{text}'")
                await self._process_inbound_command(text)

            # Photo Message
            photos = message.get("photo", [])
            if photos:
                # Get highest res photo
                best_photo = photos[-1]
                file_id = best_photo.get("file_id")
                caption = message.get("caption", "Analyze this image.")
                
                await self.send_text_async("📸 Downloading image for Vision analysis...")
                local_path = await self._download_file(file_id, ".jpg")
                if local_path:
                    # Convert to base64 for Gemini
                    with open(local_path, "rb") as img_f:
                        b64 = base64.b64encode(img_f.read()).decode("utf-8")
                    
                    # Clean up
                    try: os.remove(local_path)
                    except: pass
                    
                    # Inject into Gemini
                    prompt = f"[PHONE IMAGE RECEIVED from Boss. Base64 payload attached. Please analyze this image based on the caption: '{caption}'.]\n[BASE64_IMG:{b64}]"
                    await self._process_inbound_command(prompt, raw_inject=True)

            # Voice Note
            voice = message.get("voice")
            if voice:
                file_id = voice.get("file_id")
                await self.send_text_async("🎤 Transcribing voice note via Gemini...")
                local_path = await self._download_file(file_id, ".ogg")
                if local_path:
                    # Inform orchestrator/bridge to transcribe this OGG file via Gemini API
                    prompt = f"[PHONE VOICE NOTE RECEIVED from Boss at path: {local_path}. Please transcribe this audio file and respond to the content.]"
                    await self._process_inbound_command(prompt, raw_inject=True)

            # Location
            location = message.get("location")
            if location:
                lat = location.get("latitude")
                lon = location.get("longitude")
                prompt = f"Boss sent location from phone: Lat {lat}, Lon {lon}. Provide weather and a brief summary for this location."
                await self._process_inbound_command(prompt, raw_inject=True)

        # Inline Button Callback
        callback = update.get("callback_query", {})
        if callback:
            cb_id   = callback.get("id")
            cb_data = callback.get("data", "")
            from_id = str(callback.get("message", {}).get("chat", {}).get("id", ""))

            if from_id == self.chat_id:
                try:
                    await self._http.post(
                        f"{self._base_url}/answerCallbackQuery",
                        json={"callback_query_id": cb_id, "text": "✅ Received!"}
                    )
                except: pass
                
                if cb_data.startswith("cmd:"):
                    cmd = cb_data.split("cmd:", 1)[1]
                    await self.send_text_async(f"✅ Processing: {cmd}", button_set="none")
                    await self._process_inbound_command(cmd)
                elif cb_data == "done":
                    pass

    async def _process_inbound_command(self, text: str, raw_inject: bool = False):
        """
        Smart processing of inbound commands.
        If it's a known PC command (e.g., 'volume up'), bypass Gemini and execute directly.
        Otherwise, queue for Gemini injection.
        """
        if not raw_inject:
            from core.command_parser import parse_command
            from core.sivi_controller import controller
            
            # Try to parse it as a direct PC command
            cmd = parse_command(text)
            
            # If it's a direct operational command, bypass Gemini for instant execution
            instant_cmds = ["VOLUME_UP", "VOLUME_DOWN", "MUTE", "TAKE_SCREENSHOT", "LOCK_SCREEN", "SLEEP", "BRIGHTNESS_UP", "BRIGHTNESS_DOWN"]
            
            if cmd and cmd.type in instant_cmds:
                logger.info(f"[MobileHandoff] Instant bypass execution for: {cmd.type}")
                try:
                    res = await asyncio.to_thread(controller.execute_command, cmd)
                    await self.send_text_async(f"✅ Executed: {cmd.type}\nResult: {res}", button_set="none")
                    return
                except Exception as e:
                    await self.send_text_async(f"❌ Failed: {e}", button_set="none")
                    return

        # Not an instant bypass command — inject into Gemini stream
        # If Gemini is disconnected, queue it.
        if self._command_callback:
            # We check connectivity state outside (in bridge_server)
            self._pending_inbound_commands.append(text)
            self.flush_pending_commands()

    def flush_pending_commands(self):
        """Called by Bridge Server when Gemini connects to flush offline queue."""
        if not self._command_callback: return
        
        while self._pending_inbound_commands:
            text = self._pending_inbound_commands.popleft()
            if text.startswith("[PHONE"):
                formatted = text
            else:
                formatted = f"[PHONE COMMAND from Boss's mobile]: {text}"
            
            success = self._command_callback(formatted)
            # If callback returns False (meaning Gemini disconnected), we put it back and break
            if success is False:
                self._pending_inbound_commands.appendleft(text)
                break

    async def close(self):
        self.stop_polling()
        await self._http.aclose()


# ── Singleton ──────────────────────────────────────────────────────────────────
mobile_handoff = MobileHandoffManager()
