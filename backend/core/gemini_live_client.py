"""
Sivi — Gemini Live WebSocket Client (PC Edition)
Connects to Google Gemini Live API via WebSocket BidiGenerateContent.
Handles: setup, mic audio streaming, text messages, keepalive, session renewal.

Protocol: wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent
"""

import asyncio
import base64
import json
import time
import logging
from typing import Callable, Optional

import websockets

logger = logging.getLogger("sivi.gemini_live")

# Key pool import — safe: falls back gracefully if pool unavailable
try:
    from gemini_key_pool import key_pool as _key_pool
except Exception:
    _key_pool = None

# ── Constants ─────────────────────────────────────────────────────

WS_BASE_URL = "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent"

SESSION_RENEW_AFTER = 540    # 9 minutes — renew session before 10min timeout
KEEPALIVE_INTERVAL = 8       # seconds — send silent PCM chunk
RECONNECT_DELAY = 3          # seconds — delay before auto-reconnect

# Silent PCM chunk (1024 bytes of silence at 16kHz mono 16-bit)
SILENT_CHUNK = base64.b64encode(b'\x00' * 1024).decode('utf-8')

# ── Available Models ──────────────────────────────────────────────

MODELS = {
    "native_audio": {
        "label": "Native Audio (Human Voice)",
        "model": "models/gemini-2.5-flash-native-audio-preview-12-2025",
    },
    "flash_live": {
        "label": "Flash Live (Fast)",
        "model": "models/gemini-2.0-flash-live-001",
    },
    "pro_audio": {
        "label": "Pro Audio Dialog",
        "model": "models/gemini-2.5-flash-preview-native-audio-dialog",
    },
}

# ── Available Voices ──────────────────────────────────────────────

VOICES = [
    {"id": "Aoede", "label": "Aoede (Female)", "gender": "female"},
    {"id": "Charon", "label": "Charon (Male)", "gender": "male"},
    {"id": "Kore", "label": "Kore (Female)", "gender": "female"},
    {"id": "Fenrir", "label": "Fenrir (Male)", "gender": "male"},
    {"id": "Puck", "label": "Puck (Male)", "gender": "male"},
    {"id": "Leda", "label": "Leda (Female)", "gender": "female"},
    {"id": "Orus", "label": "Orus (Male)", "gender": "male"},
    {"id": "Zephyr", "label": "Zephyr (Female)", "gender": "female"},
]


class GeminiLiveClient:
    """
    WebSocket client for Gemini Live BidiGenerateContent API.
    Mirrors the Android Sivi protocol exactly.

    Key rotation:
      Pulls its API key from GeminiKeyPool on every connect attempt.
      On 429 / quota errors reports back to pool so next connect
      uses the next healthy key automatically.
    """

    def __init__(
        self,
        api_key: str = "",          # kept for backward compat; pool takes precedence
        model: str = "models/gemini-2.5-flash-native-audio-preview-12-2025",
        voice: str = "Aoede",
        system_prompt: str = "",
        temperature: float = 0.7,
    ):
        self._fallback_api_key = api_key  # used only if key pool is unavailable
        self.api_key = self._pick_key()   # active key for current attempt
        self.model = model
        self.voice = voice
        self.system_prompt = system_prompt
        self.temperature = temperature

        # Connection state
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._connected = False
        self._session_start_time = 0.0
        self._should_run = False

        # Tasks
        self._receive_task: Optional[asyncio.Task] = None
        self._keepalive_task: Optional[asyncio.Task] = None
        self._session_renewal_task: Optional[asyncio.Task] = None

        # Transcript buffers
        self._input_buffer = ""
        self._output_buffer = ""

        # ── Callbacks ─────────────────────────────────────────────
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_audio_received: Optional[Callable[[bytes], None]] = None
        self.on_input_transcript: Optional[Callable[[str], None]] = None
        self.on_output_transcript: Optional[Callable[[str], None]] = None
        self.on_turn_complete: Optional[Callable[[str, str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_setup_complete: Optional[Callable] = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _pick_key(self) -> str:
        """Get the best available key from the pool, or fallback."""
        if _key_pool is not None:
            return _key_pool.get()
        return self._fallback_api_key

    def _build_ws_url(self) -> str:
        # Always fetch a fresh key — pool returns least-used / not-cooling key
        self.api_key = self._pick_key()
        return f"{WS_BASE_URL}?key={self.api_key}"

    def _build_setup_message(self) -> dict:
        """Build the setup message matching the Sivi protocol."""
        return {
            "setup": {
                "model": self.model,
                "system_instruction": {
                    "parts": [{"text": self.system_prompt}]
                },
                "generation_config": {
                    "response_modalities": ["AUDIO"],
                    "speech_config": {
                        "voice_config": {
                            "prebuilt_voice_config": {
                                "voice_name": self.voice
                            }
                        }
                    },
                    "temperature": self.temperature,
                },
                "output_audio_transcription": {},
                "input_audio_transcription": {},
            }
        }

    async def connect(self):
        """Connect to Gemini Live WebSocket with auto-reconnect + key rotation."""
        self._should_run = True

        while self._should_run:
            current_key = self._pick_key()   # fresh key each attempt
            self.api_key = current_key
            url = f"{WS_BASE_URL}?key={current_key}"

            try:
                logger.info(
                    f"Connecting to Gemini Live... "
                    f"Model: {self.model}, Voice: {self.voice}, "
                    f"Key: ...{current_key[-6:]}"
                )

                self._ws = await websockets.connect(
                    url,
                    max_size=None,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=5,
                )

                # Send setup message
                setup_msg = self._build_setup_message()
                await self._ws.send(json.dumps(setup_msg))
                logger.info("Setup message sent, waiting for setupComplete...")

                # Wait for setupComplete
                response = await self._ws.recv()
                data = json.loads(response)

                if "setupComplete" in data:
                    self._connected = True
                    self._session_start_time = time.time()
                    logger.info("✅ Gemini Live session established!")

                    if self.on_setup_complete:
                        self.on_setup_complete()
                    if self.on_connected:
                        self.on_connected()

                    # Start background tasks
                    self._receive_task = asyncio.create_task(self._receive_loop())
                    self._keepalive_task = asyncio.create_task(self._keepalive_loop())
                    self._session_renewal_task = asyncio.create_task(self._session_renewal_loop())

                    # Wait for receive task to complete (disconnection)
                    await self._receive_task
                else:
                    logger.warning(f"Unexpected setup response: {data}")

            except websockets.exceptions.ConnectionClosedError as e:
                err = str(e)
                logger.warning(f"WebSocket closed: {err}")
                # Detect quota / auth errors and report to pool
                if _key_pool:
                    if "429" in err or "quota" in err.lower() or "resource_exhausted" in err.lower():
                        _key_pool.report_quota(current_key)
                        logger.info(f"[KeyPool] Reported quota on ...{current_key[-6:]} — next key on reconnect")
                    elif "401" in err or "unauthenticated" in err.lower() or "invalid" in err.lower():
                        _key_pool.report_invalid(current_key)
                        logger.error(f"[KeyPool] Reported invalid on ...{current_key[-6:]}")

            except Exception as e:
                logger.error(f"Connection error: {e}")
                if self.on_error:
                    self.on_error(str(e))
            finally:
                self._connected = False
                self._cancel_tasks()
                if self.on_disconnected:
                    self.on_disconnected()

            # Auto-reconnect with delay
            if self._should_run:
                logger.info(f"Reconnecting in {RECONNECT_DELAY}s...")
                await asyncio.sleep(RECONNECT_DELAY)

    async def disconnect(self):
        """Gracefully disconnect."""
        self._should_run = False
        self._connected = False
        self._cancel_tasks()
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
        logger.info("Disconnected from Gemini Live")

    def _cancel_tasks(self):
        """Cancel all background tasks."""
        for task in [self._receive_task, self._keepalive_task, self._session_renewal_task]:
            if task and not task.done():
                task.cancel()

    # ── Send Methods ──────────────────────────────────────────────

    async def send_audio(self, pcm_bytes: bytes):
        """Send mic audio chunk (16kHz PCM) to Gemini."""
        if not self._connected or not self._ws:
            return

        b64_data = base64.b64encode(pcm_bytes).decode('utf-8')
        msg = {
            "realtime_input": {
                "media_chunks": [{
                    "mime_type": "audio/pcm;rate=16000",
                    "data": b64_data,
                }]
            }
        }
        try:
            await self._ws.send(json.dumps(msg))
        except Exception as e:
            logger.error(f"Error sending audio: {e}")

    async def send_text(self, text: str):
        """Send text message to Gemini (like typing a message)."""
        if not self._connected or not self._ws:
            return

        msg = {
            "client_content": {
                "turns": [{"role": "user", "parts": [{"text": text}]}],
                "turn_complete": True,
            }
        }
        try:
            await self._ws.send(json.dumps(msg))
            logger.info(f"Sent text to Gemini: {text[:50]}...")
        except Exception as e:
            logger.error(f"Error sending text: {e}")

    async def send_interrupt(self):
        """Interrupt Sivi while she's speaking."""
        if not self._connected or not self._ws:
            return

        msg = {
            "client_content": {
                "turns": [],
                "turn_complete": True,
            }
        }
        try:
            await self._ws.send(json.dumps(msg))
            logger.info("Sent interrupt signal")
        except Exception as e:
            logger.error(f"Error sending interrupt: {e}")

    # ── Receive Loop ──────────────────────────────────────────────

    async def _receive_loop(self):
        """Main loop to receive and parse messages from Gemini."""
        try:
            async for message in self._ws:
                try:
                    data = json.loads(message)
                    self._parse_server_message(data)
                except json.JSONDecodeError:
                    logger.warning("Received non-JSON message")
                except Exception as e:
                    logger.error(f"Error parsing message: {e}")
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except asyncio.CancelledError:
            pass

    def _parse_server_message(self, data: dict):
        """Parse serverContent fields from Gemini response."""
        server_content = data.get("serverContent", {})

        if not server_content:
            return

        # ── Audio data (Sivi speaking) ────────────────────────────
        model_turn = server_content.get("modelTurn", {})
        parts = model_turn.get("parts", [])

        for part in parts:
            inline_data = part.get("inlineData", {})
            audio_b64 = inline_data.get("data")
            if audio_b64:
                audio_bytes = base64.b64decode(audio_b64)
                if self.on_audio_received:
                    self.on_audio_received(audio_bytes)

        # ── Output transcription (what Sivi said) ─────────────────
        output_transcription = server_content.get("outputTranscription", {})
        output_text = output_transcription.get("text", "")
        if output_text:
            self._output_buffer += output_text
            if self.on_output_transcript:
                self.on_output_transcript(output_text)

        # ── Input transcription (what user said) ──────────────────
        input_transcription = server_content.get("inputTranscription", {})
        input_text = input_transcription.get("text", "")
        if input_text:
            self._input_buffer += input_text
            if self.on_input_transcript:
                self.on_input_transcript(input_text)

        # ── Turn complete ─────────────────────────────────────────
        if server_content.get("turnComplete"):
            if self.on_turn_complete:
                self.on_turn_complete(
                    self._input_buffer.strip(),
                    self._output_buffer.strip()
                )
            # Reset buffers
            self._input_buffer = ""
            self._output_buffer = ""

    # ── Keepalive Loop ────────────────────────────────────────────

    async def _keepalive_loop(self):
        """Send silent PCM chunk every KEEPALIVE_INTERVAL to keep session alive."""
        try:
            while self._connected and self._ws:
                await asyncio.sleep(KEEPALIVE_INTERVAL)
                if self._connected and self._ws:
                    msg = {
                        "realtime_input": {
                            "media_chunks": [{
                                "mime_type": "audio/pcm;rate=16000",
                                "data": SILENT_CHUNK,
                            }]
                        }
                    }
                    try:
                        await self._ws.send(json.dumps(msg))
                    except Exception:
                        break
        except asyncio.CancelledError:
            pass

    # ── Session Renewal Loop ──────────────────────────────────────

    async def _session_renewal_loop(self):
        """Renew session before 10-minute timeout."""
        try:
            while self._connected:
                await asyncio.sleep(10)  # Check every 10 seconds
                elapsed = time.time() - self._session_start_time
                if elapsed >= SESSION_RENEW_AFTER:
                    logger.info("Session approaching timeout, renewing...")
                    # Close current connection — auto-reconnect will handle the rest
                    if self._ws:
                        await self._ws.close()
                    break
        except asyncio.CancelledError:
            pass

    # ── Config Update ─────────────────────────────────────────────

    def update_config(
        self,
        model: Optional[str] = None,
        voice: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """Update config for next connection. Requires reconnect to take effect."""
        if model:
            self.model = model
        if voice:
            self.voice = voice
        if system_prompt is not None:
            self.system_prompt = system_prompt
        if temperature is not None:
            self.temperature = temperature

    @staticmethod
    def get_models() -> list[dict]:
        """Return available models for UI."""
        return [
            {"id": k, "label": v["label"], "model": v["model"]}
            for k, v in MODELS.items()
        ]

    @staticmethod
    def get_voices() -> list[dict]:
        """Return available voices for UI."""
        return VOICES.copy()
