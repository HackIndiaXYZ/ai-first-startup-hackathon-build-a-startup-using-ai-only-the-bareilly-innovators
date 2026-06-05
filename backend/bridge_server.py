"""
Sivi — PC AI Voice Assistant Bridge Server
FastAPI REST API + WebSocket for frontend communication.
Integrates Gemini Live WebSocket, Audio Engine, Command Parser, and PC Actions.

Base URL: http://localhost:8000
"""

import sys
import os
import json
import asyncio
import base64
import logging
import time
import psutil
import re
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import uvicorn

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("sivi.bridge")

# Add core/ to path FIRST so all core imports resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))

from core.gemini_live_client import GeminiLiveClient, MODELS, VOICES
from core.audio_engine import AudioEngine
from core.command_parser import parse_command
from core.personality import build_system_prompt, get_greeting, get_personality_list, PERSONALITIES
from core.jarvis_controller import controller

# ══════════════════════════════════════════════════════════════════
# GLOBAL STATE
# ══════════════════════════════════════════════════════════════════

gemini_client: Optional[GeminiLiveClient] = None
audio_engine: Optional[AudioEngine] = None
voice_task: Optional[asyncio.Task] = None

# Store the main event loop for thread-safe cross-thread callbacks
_main_loop: Optional[asyncio.AbstractEventLoop] = None

# In-memory stores
command_history: list[dict] = []

CHAT_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "sivi_chat_history.json")

def load_chat_history() -> list[dict]:
    if os.path.exists(CHAT_HISTORY_FILE):
        try:
            with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
            now = time.time()
            two_days_sec = 48 * 3600
            # Keep only messages from the last 48 hours
            filtered = [msg for msg in history if now - msg.get("timestamp", 0) <= two_days_sec]
            return filtered[-200:]
        except Exception as e:
            logger.error(f"Failed to load chat history: {e}")
    return []

def save_chat_history():
    try:
        with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(chat_messages, f)
    except Exception as e:
        logger.error(f"Failed to save chat history: {e}")

chat_messages: list[dict] = load_chat_history()
connected_clients: list[WebSocket] = []

# State
sivi_state = {
    "orb_state": "idle",       # idle, listening, speaking, thinking
    "status_text": "Tap karke bolo",
    "is_muted": False,
    "is_connected": False,
    "amplitude": 0.0,
}

# Settings (loaded from env / SharedPreferences-style JSON)
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "sivi_settings.json")


def load_settings() -> dict:
    """Load settings from file or return defaults."""
    defaults = {
        "api_key": os.getenv("GEMINI_API_KEY", ""),
        "user_name": os.getenv("USER_NAME", "Rao Alok Yadav"),
        "personality_mode": os.getenv("AI_MODE", "gf"),
        "gemini_model": "native_audio",
        "gemini_voice": "Aoede",
        "temperature": 0.7,
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                saved = json.load(f)
                defaults.update(saved)
        except Exception:
            pass
    return defaults


def save_settings(settings: dict):
    """Save settings to file."""
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving settings: {e}")


settings = load_settings()

# ══════════════════════════════════════════════════════════════════
# BROADCAST HELPER
# ══════════════════════════════════════════════════════════════════

async def broadcast(event: dict):
    """Send event to all connected WebSocket clients."""
    dead = []
    for ws in connected_clients:
        try:
            await ws.send_json(event)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in connected_clients:
            connected_clients.remove(ws)


def broadcast_sync(event: dict):
    """
    Thread-safe fire-and-forget broadcast from any thread.
    Uses the stored main event loop reference.
    """
    if _main_loop is not None and _main_loop.is_running():
        asyncio.run_coroutine_threadsafe(broadcast(event), _main_loop)


# ══════════════════════════════════════════════════════════════════
# GEMINI LIVE + AUDIO CALLBACKS
# ══════════════════════════════════════════════════════════════════

def on_gemini_connected():
    logger.info("Gemini Live connected")
    sivi_state["is_connected"] = True
    sivi_state["orb_state"] = "listening"
    sivi_state["status_text"] = "Sun rahi hoon..."
    broadcast_sync({"type": "state", **sivi_state})


def on_gemini_disconnected():
    logger.info("Gemini Live disconnected")
    sivi_state["is_connected"] = False
    sivi_state["orb_state"] = "idle"
    sivi_state["status_text"] = "Disconnected..."
    broadcast_sync({"type": "state", **sivi_state})


def on_audio_received(pcm_bytes: bytes):
    """Received audio from Gemini -> queue for speaker playback."""
    if audio_engine:
        audio_engine.queue_audio(pcm_bytes)


def on_input_transcript(text: str):
    """User speech transcription fragment."""
    broadcast_sync({"type": "input_transcript", "text": text})


def on_output_transcript(text: str):
    """Sivi speech transcription fragment."""
    broadcast_sync({"type": "output_transcript", "text": text})


def on_turn_complete(user_text: str, sivi_text: str):
    """Full turn complete — add to chat and parse commands."""
    logger.info(f"Turn: User='{user_text[:60]}' | Sivi='{sivi_text[:60]}'")

    # Extract PC Command from Sivi's text
    extracted_cmd = ""
    if sivi_text:
        match = re.search(r'\[CMD:\s*(.*?)\]', sivi_text, re.IGNORECASE)
        if match:
            extracted_cmd = match.group(1).strip()
            # Remove the command tag from the visible text
            sivi_text = re.sub(r'\[CMD:\s*.*?\]', '', sivi_text, flags=re.IGNORECASE).strip()

    # Add to chat
    if user_text:
        msg_user = {"text": user_text, "is_user": True, "timestamp": time.time()}
        chat_messages.append(msg_user)
        broadcast_sync({"type": "chat_message", **msg_user})

    if sivi_text:
        msg_sivi = {"text": sivi_text, "is_user": False, "timestamp": time.time()}
        # Deduplication: skip if identical to last Sivi message
        if not chat_messages or chat_messages[-1].get("text") != sivi_text:
            chat_messages.append(msg_sivi)
            broadcast_sync({"type": "chat_message", **msg_sivi})

    # Memory Management: Prevent unbounded growth
    while len(chat_messages) > 200:
        chat_messages.pop(0)
        
    save_chat_history()

    # Execute the extracted command
    if extracted_cmd:
        cmd = parse_command(extracted_cmd)
        if cmd:
            logger.info(f"Parsed command from tag: {cmd.type} -> {cmd.params}")
            
            if cmd.type == "SWITCH_MODE":
                mode = cmd.params.get("mode", "gf")
                settings["personality_mode"] = mode
                save_settings(settings)
                result = f"Personality mode updated to {mode}. Restarting brain to apply..."
                broadcast_sync({"type": "settings_updated", "settings": settings})
                async def _delayed_switch():
                    # Allow Sivi to finish her sentence before abruptly killing the audio engine
                    await asyncio.sleep(3.5)
                    await start_voice_session(is_switch=True)

                if _main_loop:
                    asyncio.run_coroutine_threadsafe(_delayed_switch(), _main_loop)
            else:
                async def _execute_and_feedback():
                    try:
                        # Offload blocking execution to a separate thread to prevent deadlocking Gemini loop
                        result = await asyncio.to_thread(controller.execute_command, cmd)
                        
                        if result:
                            entry = {
                                "type": "command",
                                "command": extracted_cmd,
                                "response": result,
                                "timestamp": datetime.now().isoformat()
                            }
                            broadcast_sync(entry)
                            
                            # Feed sensory/complex commands back to Sivi so she speaks it naturally
                            dev_commands = ["DEV_RUN_CMD", "DEV_GIT_STATUS", "DEV_KILL_PORT", "DEV_ANALYZE_CODE", "DEV_GENERATE_CODE"]
                            speak_commands = ["READ_CLIPBOARD", "READ_WINDOWS", "ANALYZE_EMOTION", "DESCRIBE_SCENE", "SYSTEM_STATUS", "READ_SCREEN", "NEWS", "SEARCH", "OPEN_APP", "FIND_FILE", "LIST_FILES", "CALENDAR_EVENTS"]
                            
                            if isinstance(result, str) and result.startswith("SYSTEM_ERROR:"):
                                if gemini_client and gemini_client.is_connected:
                                    error_prompt = f"CRITICAL ERROR: Your last command ({cmd.type}) failed with: {result}. Please apologize to the user and if you can, use your Developer Tools ([CMD: dev run cmd], [CMD: dev generate code]) to automatically debug and fix this issue on the system yourself!"
                                    await gemini_client.send_text(error_prompt)
                            elif cmd.type in speak_commands or cmd.type in dev_commands:
                                if gemini_client and gemini_client.is_connected:
                                    if cmd.type == "ANALYZE_EMOTION":
                                        feedback_prompt = (f"I just looked at the user through the webcam. Here is the visual analysis: '{result}'. "
                                                           f"Respond to them in your Hinglish persona (e.g. 'Aapka mood sahi nahi hai, kya hua aapko?'). "
                                                           f"Deeply analyze their state, try to convince them to be happy, and offer a specific action like playing a song or telling a joke.")
                                    elif cmd.type == "DESCRIBE_SCENE":
                                        feedback_prompt = f"I took a photo. Here is what I see: '{result}'. Describe this naturally to the user in your persona."
                                    elif cmd.type in dev_commands:
                                        feedback_prompt = f"System executed your developer command. Here is the raw terminal/system output:\n{result}\nPlease explain this output technically to the user in your Developer Persona."
                                    elif cmd.type == "READ_SCREEN":
                                        feedback_prompt = f"Here is the raw text from the screen: {result}\nPlease summarize this or read it aloud naturally to the user."
                                    elif cmd.type == "OPEN_APP":
                                        feedback_prompt = f"System attempted to open the app. Result: {result}\nIf it failed, tell the user gracefully and ask if they'd like you to search for it online or do something else. If it succeeded, confirm it playfully/professionally."
                                    else:
                                        feedback_prompt = f"System Action Result: {result}\nPlease convey this to the user naturally."
                                        
                                    await gemini_client.send_text(feedback_prompt)
                    except Exception as e:
                        logger.error(f"Command execution error: {e}")

                if _main_loop:
                    asyncio.run_coroutine_threadsafe(_execute_and_feedback(), _main_loop)
        else:
            logger.warning(f"Failed to parse AI command tag: {extracted_cmd}")
            if gemini_client and gemini_client.is_connected and _main_loop:
                error_prompt = f"SYSTEM_ERROR: Your command tag `[CMD: {extracted_cmd}]` was not recognized by the parser. Please refer to your instructions for the correct command syntax and try again, or use [CMD: remember ...] to memorize the correct mapping if the user just taught it to you."
                asyncio.run_coroutine_threadsafe(gemini_client.send_text(error_prompt), _main_loop)

    # Update state
    sivi_state["orb_state"] = "listening"
    sivi_state["status_text"] = "Sun rahi hoon..."
    broadcast_sync({"type": "state", **sivi_state})


def on_speaking_started():
    sivi_state["orb_state"] = "speaking"
    sivi_state["status_text"] = "Bol rahi hoon..."
    broadcast_sync({"type": "state", **sivi_state})


def on_speaking_stopped():
    sivi_state["orb_state"] = "listening"
    sivi_state["status_text"] = "Sun rahi hoon..."
    broadcast_sync({"type": "state", **sivi_state})


def on_mic_amplitude(amplitude: float):
    sivi_state["amplitude"] = float(amplitude)
    broadcast_sync({"type": "amplitude", "value": float(amplitude)})


def on_mic_chunk(pcm_bytes: bytes):
    """
    Mic audio chunk -> send to Gemini via WebSocket.
    This is called from a background audio thread, so we must use
    run_coroutine_threadsafe for thread-safe async dispatch.
    """
    if gemini_client and gemini_client.is_connected and _main_loop is not None:
        try:
            asyncio.run_coroutine_threadsafe(
                gemini_client.send_audio(pcm_bytes),
                _main_loop
            )
        except Exception as e:
            logger.debug(f"Mic chunk dispatch error: {e}")


def on_gemini_error(error: str):
    logger.error(f"Gemini error: {error}")
    broadcast_sync({"type": "error", "message": error})


# ══════════════════════════════════════════════════════════════════
# VOICE SESSION MANAGEMENT
# ══════════════════════════════════════════════════════════════════

async def start_voice_session(is_switch: bool = False):
    """Start the Gemini Live WebSocket + Audio Engine."""
    global gemini_client, audio_engine, voice_task

    api_key = settings.get("api_key", "")
    if not api_key:
        logger.error("No API key configured!")
        return {"error": "No API key. Set it in Settings."}

    # Resolve model string
    model_key = settings.get("gemini_model", "native_audio")
    model_info = MODELS.get(model_key, MODELS["native_audio"])
    model_str = model_info["model"]

    voice = settings.get("gemini_voice", "Aoede")
    user_name = settings.get("user_name", "Rao Alok Yadav")
    personality = settings.get("personality_mode", "gf")
    system_prompt = build_system_prompt(user_name, personality)

    # Inject recent command history for self-learning / context memory
    if command_history:
        recent = command_history[-5:]
        history_str = "\n".join([f"- User asked '{c['command']}' and System executed: '{c['response']}'" for c in recent])
        system_prompt += f"\n\nRECENT COMMAND HISTORY:\n{history_str}\n(Use this history to understand the context of what you just did or what failed.)\n"

    # Stop existing session if any
    await stop_voice_session()

    # Create Gemini client
    gemini_client = GeminiLiveClient(
        api_key=api_key,
        model=model_str,
        voice=voice,
        system_prompt=system_prompt,
        temperature=settings.get("temperature", 0.9),
    )

    # Wire callbacks
    gemini_client.on_connected = on_gemini_connected
    gemini_client.on_disconnected = on_gemini_disconnected
    gemini_client.on_audio_received = on_audio_received
    gemini_client.on_input_transcript = on_input_transcript
    gemini_client.on_output_transcript = on_output_transcript
    gemini_client.on_turn_complete = on_turn_complete
    gemini_client.on_error = on_gemini_error

    def on_setup():
        """After Gemini setup completes, start audio and send greeting."""
        global audio_engine
        audio_engine = AudioEngine()
        audio_engine.on_audio_chunk = on_mic_chunk
        audio_engine.on_amplitude_changed = on_mic_amplitude
        audio_engine.on_speaking_started = on_speaking_started
        audio_engine.on_speaking_stopped = on_speaking_stopped

        audio_engine.start_recording()
        audio_engine.start_playback()

        # Send greeting after a short delay to let audio settle
        if is_switch:
            greeting = f"(System reconnected successfully in {personality} mode.)"
        else:
            greeting = get_greeting(user_name, personality)
            
        if _main_loop is not None and _main_loop.is_running():
            asyncio.run_coroutine_threadsafe(
                _send_greeting_delayed(greeting, is_switch),
                _main_loop
            )

    gemini_client.on_setup_complete = on_setup

    # Start connection in background task
    voice_task = asyncio.create_task(gemini_client.connect())

    sivi_state["orb_state"] = "thinking"
    sivi_state["status_text"] = "Connecting..."
    await broadcast({"type": "state", **sivi_state})

    return {"status": "started", "model": model_str, "voice": voice}


async def _send_greeting_delayed(greeting: str, is_switch: bool = False):
    """Send greeting after a short delay to let audio settle."""
    await asyncio.sleep(0.8)
    
    # Desktop Notification
    try:
        from plyer import notification
        await asyncio.to_thread(
            notification.notify,
            title="Sivi AI",
            message="Sivi is now online and listening to you.",
            app_name="Sivi",
            timeout=3
        )
    except Exception as e:
        logger.error(f"Notification error: {e}")

    if gemini_client and gemini_client.is_connected:
        if is_switch:
            # Skip heavy startup context loading when just hot-swapping personality
            await gemini_client.send_text(greeting)
            sivi_state["orb_state"] = "thinking"
            sivi_state["status_text"] = "Soch rahi hoon..."
            await broadcast({"type": "state", **sivi_state})
            return

        # Inject Camera & Screen Context automatically on startup
        try:
            from core.camera_vision import camera_vision
            from core.screen_reader import screen_reader
            
            logger.info("Gathering startup context (Vision & Screen)...")
            sivi_state["status_text"] = "Looking at you..."
            broadcast_sync({"type": "state", **sivi_state})
            
            # Run in thread so we don't block the async loop
            emotion_ctx = await asyncio.to_thread(camera_vision.analyze_emotion)
            screen_ctx = await asyncio.to_thread(screen_reader.read_screen, "Summarize what's on the screen briefly in 1 sentence.")
            
            context_msg = f"\n\n[STARTUP CONTEXT: I just looked at the user through the webcam and saw: '{emotion_ctx}'. I also looked at their PC screen and saw: '{screen_ctx}'. Tailor your greeting to comment on their mood and what they are currently doing on the PC!]"
            greeting += context_msg
        except Exception as e:
            logger.error(f"Startup context error: {e}")

        await gemini_client.send_text(greeting)
        sivi_state["orb_state"] = "thinking"
        sivi_state["status_text"] = "Soch rahi hoon..."
        await broadcast({"type": "state", **sivi_state})


async def stop_voice_session():
    """Stop the Gemini Live session and audio engine."""
    global gemini_client, audio_engine, voice_task

    if audio_engine:
        audio_engine.release()
        audio_engine = None

    if gemini_client:
        await gemini_client.disconnect()
        gemini_client = None

    if voice_task and not voice_task.done():
        voice_task.cancel()
        try:
            await voice_task
        except asyncio.CancelledError:
            pass
        voice_task = None

    sivi_state["is_connected"] = False
    sivi_state["orb_state"] = "idle"
    sivi_state["status_text"] = "Offline"
    await broadcast({"type": "state", **sivi_state})


# ══════════════════════════════════════════════════════════════════
# FASTAPI APP
# ══════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    global _main_loop
    # Capture the event loop at startup for thread-safe callbacks
    _main_loop = asyncio.get_running_loop()
    logger.info("Sivi Bridge Server starting... Event loop captured.")
    
    # Start background tasks
    notif_task = asyncio.create_task(notification_worker())
    health_task = asyncio.create_task(system_health_worker())
    
    yield
    
    notif_task.cancel()
    health_task.cancel()
    logger.info("Shutting down Sivi...")
    await stop_voice_session()

async def system_health_worker():
    """Background task to proactively monitor CPU and RAM usage."""
    import psutil
    while True:
        try:
            if gemini_client and gemini_client.is_connected and sivi_state.get("orb_state") in ["listening", "idle"]:
                # Use a small interval to get a quick reading, offloaded to thread to avoid blocking event loop
                cpu_usage = await asyncio.to_thread(psutil.cpu_percent, 0.1)
                ram_percent = psutil.virtual_memory().percent
                
                # If system is under heavy load, proactively alert the user
                if cpu_usage > 90 or ram_percent > 90:
                    alert_msg = f"[SYSTEM ALERT: Background check detected high usage! CPU is at {cpu_usage}% and RAM is at {ram_percent}%. Warn the user proactively and ask if they want to close any apps.]"
                    
                    sivi_state["orb_state"] = "thinking"
                    sivi_state["status_text"] = "High system load detected..."
                    await broadcast({"type": "state", **sivi_state})
                    
                    await gemini_client.send_text(alert_msg)
                    
                    # Sleep longer after an alert to avoid spamming
                    await asyncio.sleep(120)
                    continue
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Health worker error: {e}")
            
        await asyncio.sleep(30)  # Normal check every 30 seconds

async def notification_worker():
    """Background worker to check for new Windows notifications and alert Sivi."""
    from core.notification_monitor import notification_monitor
    while True:
        try:
            await asyncio.sleep(5)
            if sivi_state.get("is_connected") and gemini_client and gemini_client.is_connected:
                # Only alert if we aren't currently speaking (to avoid interrupting too much)
                if sivi_state.get("orb_state") in ["listening", "idle"]:
                    alerts = await notification_monitor._get_new_notifications_async()
                    if alerts:
                        alert_text = " | ".join(alerts)
                        logger.info(f"New Notifications Detected: {alert_text}")
                        # Send context to Gemini to announce it
                        prompt = f"[SYSTEM ALERT: The user just received new PC notifications: '{alert_text}'. Inform them immediately in a short, conversational, and helpful way.]"
                        await gemini_client.send_text(prompt)
                        sivi_state["orb_state"] = "thinking"
                        sivi_state["status_text"] = "Reading notification..."
                        await broadcast({"type": "state", **sivi_state})
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Notification worker error: {e}")
            await asyncio.sleep(5)



app = FastAPI(
    title="Sivi AI Voice Assistant API",
    description="REST API + WebSocket bridge for Sivi PC voice assistant.",
    version="2.1.0",
    lifespan=lifespan,
)

# CORS — allow all origins for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic Models ───────────────────────────────────────────────

class CommandRequest(BaseModel):
    command: str

class TextMessageRequest(BaseModel):
    text: str

class SettingsUpdateRequest(BaseModel):
    api_key: Optional[str] = None
    user_name: Optional[str] = None
    personality_mode: Optional[str] = None
    gemini_model: Optional[str] = None
    gemini_voice: Optional[str] = None
    temperature: Optional[float] = None


# ── REST Endpoints ────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {
        "status": "online",
        "version": "2.1.0",
        "voice_connected": sivi_state["is_connected"],
        "modules": len(controller.get_module_status()),
        "uptime": datetime.now().isoformat(),
    }


@app.get("/status")
async def get_status():
    return {
        "status": "online",
        "sivi_state": sivi_state,
        "modules": controller.get_module_status(),
        "settings": {k: v for k, v in settings.items() if k != "api_key"},
        "has_api_key": bool(settings.get("api_key")),
    }


@app.get("/system-info")
async def get_system_info():
    """Return system stats for the top bar."""
    try:
        battery = psutil.sensors_battery()
        battery_percent = battery.percent if battery else -1
        battery_plugged = battery.power_plugged if battery else False
    except Exception:
        battery_percent = -1
        battery_plugged = False

    ram = psutil.virtual_memory()
    return {
        "battery_percent": battery_percent,
        "battery_plugged": battery_plugged,
        "ram_used_gb": round(ram.used / (1024**3), 1),
        "ram_total_gb": round(ram.total / (1024**3), 1),
        "ram_percent": ram.percent,
        "cpu_percent": psutil.cpu_percent(interval=0),
        "time": datetime.now().strftime("%I:%M %p"),
        "date": datetime.now().strftime("%d %b %Y"),
    }


@app.post("/command")
async def execute_command(req: CommandRequest):
    """Execute a text command through jarvis_controller."""
    response = controller.process_command(req.command)
    entry = {
        "command": req.command,
        "response": response,
        "timestamp": datetime.now().isoformat(),
    }
    command_history.append(entry)
    await broadcast({"type": "command", **entry})
    return {"status": "success", "command": req.command, "response": response}


@app.post("/voice/start")
async def start_voice():
    """Start Gemini Live voice session."""
    result = await start_voice_session()
    return result


@app.post("/voice/stop")
async def stop_voice():
    """Stop Gemini Live voice session."""
    await stop_voice_session()
    return {"status": "stopped"}


@app.post("/voice/send-text")
async def send_text_to_sivi(req: TextMessageRequest):
    """Send text message to Sivi via Gemini."""
    if not req.text.strip():
        return {"error": "Empty message"}
    if gemini_client and gemini_client.is_connected:
        # Add user text to chat instantly
        msg = {"text": req.text, "is_user": True, "timestamp": time.time()}
        chat_messages.append(msg)
        while len(chat_messages) > 200:
            chat_messages.pop(0)
        save_chat_history()
        await broadcast({"type": "chat_message", **msg})

        # Send to Gemini
        await gemini_client.send_text(req.text)
        sivi_state["orb_state"] = "thinking"
        sivi_state["status_text"] = "Soch rahi hoon..."
        await broadcast({"type": "state", **sivi_state})
        return {"status": "sent"}
    return {"error": "Not connected to Gemini Live. Start voice session first."}


@app.post("/voice/interrupt")
async def interrupt_sivi():
    """Interrupt Sivi while she's speaking."""
    if audio_engine:
        audio_engine.clear_playback_queue()
    if gemini_client and gemini_client.is_connected:
        await gemini_client.send_interrupt()
    sivi_state["orb_state"] = "listening"
    sivi_state["status_text"] = "Sun rahi hoon..."
    await broadcast({"type": "state", **sivi_state})
    return {"status": "interrupted"}


@app.post("/voice/mute")
async def toggle_mute():
    """Toggle mic mute."""
    is_muted = not sivi_state["is_muted"]
    sivi_state["is_muted"] = is_muted
    if audio_engine:
        audio_engine.set_muted(is_muted)
    await broadcast({"type": "state", **sivi_state})
    return {"status": "muted" if is_muted else "unmuted", "is_muted": is_muted}


@app.get("/chat")
async def get_chat():
    """Get chat message history."""
    return {"messages": chat_messages[-100:]}


@app.get("/history")
async def get_history():
    return {"history": command_history[-50:]}


@app.get("/settings")
async def get_settings():
    """Get current settings (API key masked)."""
    safe = {k: v for k, v in settings.items()}
    if safe.get("api_key") and len(safe["api_key"]) > 12:
        safe["api_key"] = safe["api_key"][:8] + "..." + safe["api_key"][-4:]
    return {
        "settings": safe,
        "models": GeminiLiveClient.get_models(),
        "voices": GeminiLiveClient.get_voices(),
        "personalities": get_personality_list(),
    }


@app.post("/settings")
async def update_settings(req: SettingsUpdateRequest):
    """Update settings."""
    if req.api_key is not None and "..." not in req.api_key:
        settings["api_key"] = req.api_key
    if req.user_name is not None:
        settings["user_name"] = req.user_name
    if req.personality_mode is not None:
        settings["personality_mode"] = req.personality_mode
    if req.gemini_model is not None:
        settings["gemini_model"] = req.gemini_model
    if req.gemini_voice is not None:
        settings["gemini_voice"] = req.gemini_voice
    if req.temperature is not None:
        settings["temperature"] = req.temperature

    save_settings(settings)
    return {"status": "updated", "restart_required": True}


@app.get("/modules")
async def get_modules():
    return {"modules": controller.get_module_status()}


# ── WebSocket Endpoint ────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.append(ws)
    logger.info(f"WebSocket client connected ({len(connected_clients)} total)")

    try:
        # Send initial state on connect
        await ws.send_json({
            "type": "init",
            "state": sivi_state,
            "modules": controller.get_module_status(),
            "chat": chat_messages[-50:],
        })

        while True:
            data = await ws.receive_text()
            try:
                parsed = json.loads(data)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            msg_type = parsed.get("type")

            if msg_type == "command":
                cmd_text = parsed.get("command", "").strip()
                if cmd_text:
                    response = controller.process_command(cmd_text)
                    entry = {
                        "command": cmd_text,
                        "response": response,
                        "timestamp": datetime.now().isoformat(),
                    }
                    command_history.append(entry)
                    await ws.send_json({"type": "command_response", **entry})

            elif msg_type == "send_text":
                text = parsed.get("text", "").strip()
                if text and gemini_client and gemini_client.is_connected:
                    msg = {"text": text, "is_user": True, "timestamp": time.time()}
                    chat_messages.append(msg)
                    await broadcast({"type": "chat_message", **msg})
                    await gemini_client.send_text(text)
                    sivi_state["orb_state"] = "thinking"
                    sivi_state["status_text"] = "Soch rahi hoon..."
                    await broadcast({"type": "state", **sivi_state})

            elif msg_type == "ping":
                await ws.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if ws in connected_clients:
            connected_clients.remove(ws)
        logger.info(f"WebSocket client disconnected ({len(connected_clients)} remaining)")


# ══════════════════════════════════════════════════════════════════
# STATIC FRONTEND SERVING
# ══════════════════════════════════════════════════════════════════

from fastapi.staticfiles import StaticFiles

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    logger.warning("Frontend dist directory not found. Please run 'npm run build' in the frontend folder.")

# ══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    uvicorn.run("bridge_server:app", host="127.0.0.1", port=8000, reload=False)
