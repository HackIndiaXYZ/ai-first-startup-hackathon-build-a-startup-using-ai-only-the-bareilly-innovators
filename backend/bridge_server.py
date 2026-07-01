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
from core.sivi_controller import controller
from core.self_learning import self_learning
from core.always_on_agents import agents
from core.agent_orchestrator import orchestrator

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

CHAT_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "data", "sivi_chat_history.json")

def load_chat_history() -> list[dict]:
    if os.path.exists(CHAT_HISTORY_FILE):
        try:
            with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            # Handle both formats: flat list OR {"sessions": [...]} dict
            if isinstance(raw, dict):
                history = raw.get("sessions", [])
            elif isinstance(raw, list):
                history = raw
            else:
                history = []
            now = time.time()
            two_days_sec = 48 * 3600
            # Keep only messages from the last 48 hours
            filtered = [msg for msg in history if isinstance(msg, dict) and now - msg.get("timestamp", 0) <= two_days_sec]
            return filtered[-200:]
        except Exception as e:
            logger.error(f"Failed to load chat history: {e}")
    return []

def save_chat_history():
    try:
        os.makedirs(os.path.dirname(CHAT_HISTORY_FILE), exist_ok=True)
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
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "data", "sivi_settings.json")


def load_settings() -> dict:
    """Load settings from file or return defaults."""
    defaults = {
        "api_key": os.getenv("GEMINI_API_KEY", ""),
        "user_name": os.getenv("USER_NAME", "Rao Alok Yadav"),
        "personality_mode": os.getenv("AI_MODE", "sivi"),
        "gemini_model": "native_audio",
        "gemini_voice": "Aoede",
        "temperature": 0.7,
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                saved = json.load(f)
                # If API key in settings file is a placeholder or empty, do not use it to overwrite default env var
                if saved.get("api_key") in ["", "YOUR_API_KEY_HERE", "placeholder"]:
                    saved.pop("api_key", None)
                defaults.update(saved)
        except Exception:
            pass
    return defaults


def save_settings(settings: dict):
    """Save settings to file."""
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
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
    # Smart Barge-in: If the user speaks actual words while Sivi is talking, interrupt instantly!
    if text.strip() and audio_engine and audio_engine.is_speaking:
        logger.info(f"User interrupted Sivi with: '{text}'. Clearing playback queue.")
        audio_engine.clear_playback_queue()


def on_output_transcript(text: str):
    """Sivi speech transcription fragment."""
    broadcast_sync({"type": "output_transcript", "text": text})


def on_turn_complete(user_text: str, sivi_text: str):
    """Full turn complete — add to chat and parse commands."""
    logger.info(f"Turn: User='{user_text[:60]}' | Sivi='{sivi_text[:60]}'")

    # Extract PC Commands from Sivi's text
    extracted_cmds = []
    if sivi_text:
        # Find all command tags (e.g. [CMD: open notepad] [CMD: snap to left])
        matches = re.finditer(r'\[CMD:\s*(.*?)\]', sivi_text, re.IGNORECASE)
        for match in matches:
            cmd_val = match.group(1).strip()
            # Clean up nested tags if model hallucinates them (e.g. [CMD: [CMD: open vscode]])
            if cmd_val.upper().startswith("[CMD:"):
                cmd_val = cmd_val[5:].strip()
                if cmd_val.endswith("]"):
                    cmd_val = cmd_val[:-1].strip()
            if cmd_val.upper().startswith("CMD:"):
                cmd_val = cmd_val[4:].strip()

            if cmd_val not in extracted_cmds:
                extracted_cmds.append(cmd_val)
        # Remove the command tags from the visible text
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

    # Subconscious Memory Logging
    try:
        from core.subconscious_memory import subconscious_memory
        if user_text:
            subconscious_memory.log_message("user", user_text)
        if sivi_text:
            subconscious_memory.log_message("sivi", sivi_text)
    except Exception as e:
        logger.error(f"Subconscious logging error: {e}")

    # Memory Management: Prevent unbounded growth
    while len(chat_messages) > 200:
        chat_messages.pop(0)
        
    save_chat_history()

    # ── Self-Learning: Detect user corrections ──────────────────
    if user_text:
        user_lower = user_text.lower().strip()
        correction_patterns = [
            "that's wrong", "thats wrong", "no no", "galat", "nahi",
            "not what i asked", "wrong", "i said", "i meant", "not that",
            "are you deaf", "listen properly", "galat kiya", "ye nahi",
            "kuch aur", "doosra", "fix this", "fix it", "that was wrong",
            "you messed up", "not correct", "incorrect", "idiot",
            "pagal", "bewakoof", "not like that", "aise nahi",
        ]
        if any(pat in user_lower for pat in correction_patterns):
            # The last Sivi message is what was wrong
            last_sivi = ""
            for msg in reversed(chat_messages):
                if not msg.get("is_user") and msg.get("text"):
                    last_sivi = msg["text"]
                    break
            correction_context = f"User said '{user_text}' to correct Sivi. Sivi's last response was: '{last_sivi[:100]}'"
            self_learning.log_user_correction(user_text, correction_context)
            logger.info(f"[SelfLearn] User correction detected: {user_text[:60]}")

    if extracted_cmds:
        async def _execute_and_feedback():
            all_feedback = []
            has_error = False
            
            for extracted_cmd in extracted_cmds:
                cmd = parse_command(extracted_cmd)
                if not cmd:
                    # Check if it's a workflow/macro trigger
                    from core.workflow_engine import workflow_engine
                    workflow_steps = workflow_engine.get_workflow(extracted_cmd.strip())
                    if workflow_steps:
                        logger.info(f"[WorkflowEngine] Expanding macro '{extracted_cmd}' → {workflow_steps}")
                        for step_cmd_text in workflow_steps:
                            step_cmd = parse_command(step_cmd_text)
                            if step_cmd:
                                try:
                                    step_result = await asyncio.wait_for(
                                        asyncio.to_thread(controller.execute_command, step_cmd),
                                        timeout=20.0
                                    )
                                    all_feedback.append(f"Workflow step '{step_cmd_text}': {step_result}")
                                except Exception as step_e:
                                    all_feedback.append(f"Workflow step '{step_cmd_text}' failed: {step_e}")
                                # Small delay between steps for natural pacing
                                await asyncio.sleep(0.5)
                        continue  # Skip to next CMD tag

                    logger.warning(f"Failed to parse AI command tag: {extracted_cmd}")
                    # Log to self-learning engine
                    self_learning.log_error(
                        user_text=user_text,
                        cmd_tag=extracted_cmd,
                        cmd_type="PARSE_FAIL",
                        error_msg=f"The command tag `[CMD: {extracted_cmd}]` was not recognized by the parser.",
                    )
                    all_feedback.append(f"SYSTEM_ERROR: The command tag `[CMD: {extracted_cmd}]` was not recognized.")
                    has_error = True
                    continue
                    
                logger.info(f"Parsed command from tag: {cmd.type} -> {cmd.params}")

                # ── SWITCH_MODE: Handle inline here since it changes bridge_server settings ──
                if cmd.type == "SWITCH_MODE":
                    new_mode = cmd.params.get("mode", "sivi")
                    settings["personality_mode"] = new_mode
                    save_settings(settings)
                    all_feedback.append(f"SWITCH_MODE result: Personality switched to '{new_mode}' mode. Acknowledge this to the user warmly.")
                    logger.info(f"Personality switched to: {new_mode}")
                    continue

                try:
                    # Check if AgentOrchestrator should handle this (RAG, complex logic)
                    async def async_speak(res_text):
                        if res_text and gemini_client and gemini_client.is_connected:
                            await gemini_client.send_text(f"System result for the user: {res_text}")

                    is_handled = await orchestrator.route_task(extracted_cmd, async_speak)
                    if is_handled:
                        logger.info(f"Command routed to background agent: {extracted_cmd}")
                        continue
                        
                    # Offload blocking execution to a separate thread with a failsafe timeout
                    result = None
                    error_occurred = False
                    error_msg = ""
                    stack = ""
                    
                    try:
                        result = await asyncio.wait_for(
                            asyncio.to_thread(controller.execute_command, cmd),
                            timeout=35.0
                        )
                    except asyncio.TimeoutError:
                        result = "SYSTEM_ERROR: Command execution timed out after 35 seconds."
                        error_occurred = True
                        error_msg = result
                    except Exception as exc:
                        import traceback as tb
                        stack = tb.format_exc()
                        result = f"SYSTEM_ERROR: {exc}"
                        error_occurred = True
                        error_msg = str(exc)
                    
                    # Check if the result itself is an error
                    if isinstance(result, str) and result.startswith("SYSTEM_ERROR:"):
                        error_occurred = True
                        error_msg = result
                    
                    # ── Self-Learning: Log errors & attempt auto-retry ──
                    if error_occurred:
                        journal_entry = self_learning.log_error(
                            user_text=user_text,
                            cmd_tag=extracted_cmd,
                            cmd_type=cmd.type,
                            error_msg=error_msg,
                            stack_trace=stack,
                        )
                        category = journal_entry.get("category", "CRASH")
                        
                        # Auto-retry for transient errors (timeout, network)
                        if self_learning.should_auto_retry(category, cmd.type):
                            logger.info(f"[SelfLearn] Auto-retrying {cmd.type} after {category}...")
                            try:
                                retry_result = await asyncio.wait_for(
                                    asyncio.to_thread(controller.execute_command, cmd),
                                    timeout=35.0
                                )
                                if retry_result and not str(retry_result).startswith("SYSTEM_ERROR:"):
                                    # Retry succeeded!
                                    result = retry_result
                                    error_occurred = False
                                    self_learning.mark_resolved(cmd.type, "auto_retry_success")
                                    self_learning.add_lesson(
                                        source="auto_retry_success",
                                        lesson=f"{cmd.type} failed with {category} but succeeded on retry. This is a transient error.",
                                        cmd_type=cmd.type,
                                        severity="low",
                                    )
                                    logger.info(f"[SelfLearn] Auto-retry SUCCEEDED for {cmd.type}")
                            except Exception:
                                pass  # Retry also failed, proceed with self-diagnosis
                        
                        # If still failed, trigger self-diagnosis
                        if error_occurred:
                            diagnosis_prompt = self_learning.build_diagnosis_prompt(
                                cmd_tag=extracted_cmd,
                                cmd_type=cmd.type,
                                error_msg=error_msg,
                            )
                            all_feedback.append(diagnosis_prompt)
                            has_error = True
                            
                            # Don't add the raw error separately — diagnosis includes it
                            continue
                    
                    # ── Success path: normal feedback ──
                    if result:
                        # Mark any previous errors for this cmd_type as resolved
                        self_learning.mark_resolved(cmd.type, "success_on_reattempt")
                        
                        entry = {
                            "type": "command",
                            "command": extracted_cmd,
                            "response": result,
                            "timestamp": datetime.now().isoformat()
                        }
                        command_history.append(entry)
                        if len(command_history) > 200:
                            command_history.pop(0)
                        broadcast_sync(entry)
                        
                        dev_commands = ["DEV_RUN_CMD", "DEV_GIT_STATUS", "DEV_KILL_PORT", "DEV_ANALYZE_CODE", "DEV_GENERATE_CODE", "DEV_EXECUTE_SCRIPT", "DEV_SPAWN_SUBAGENT"]
                        speak_commands = [
                            "READ_CLIPBOARD", "READ_WINDOWS", "ANALYZE_EMOTION", "ANALYZE_WELLNESS", "DESCRIBE_SCENE",
                            "SYSTEM_STATUS", "GET_WEATHER", "READ_SCREEN", "NEWS", "SEARCH", "OPEN_APP",
                            "FIND_FILE", "LIST_FILES", "CALENDAR_EVENTS", "CREATE_EVENT",
                            "MEDICAL_ADVICE", "WRITE_CLIPBOARD", "CLOSE_APP", "SWITCH_APP", "TYPE_TEXT",
                            "PRESS_KEY", "SCREENSHOT", "VOLUME_SET", "SET_TIMER",
                            "CREATE_FILE", "CREATE_FOLDER", "DELETE_FILE", "OPEN_FILE",
                            "MINIMIZE_WINDOW", "MAXIMIZE_WINDOW", "SNAP_LEFT", "SNAP_RIGHT",
                            "TAB_NEXT", "TAB_PREV", "TAB_NEW", "TAB_CLOSE",
                            "WIFI_ON", "WIFI_OFF", "BLUETOOTH_ON", "BLUETOOTH_OFF",
                            "REMEMBER", "FORGET_ALL", "SEND_EMAIL", "SEND_WHATSAPP", "WHATSAPP_READ_CHAT",
                            "PLAY_YOUTUBE", "PLAY_SPOTIFY", "LOCK_SCREEN", "VOLUME_UP", "VOLUME_DOWN",
                            "MUTE", "BRIGHTNESS_UP", "BRIGHTNESS_DOWN", "MEDIA_PLAY_PAUSE",
                            "MEDIA_NEXT", "MEDIA_PREV", "SLEEP", "SHUTDOWN",
                        ]
                        
                        if cmd.type in speak_commands or cmd.type in dev_commands:
                            if cmd.type == "ANALYZE_EMOTION":
                                all_feedback.append(
                                    f"[DEEP EMOTION ANALYSIS RESULT]: '{result}'. "
                                    f"This is what the camera detected about Boss's current emotional state. "
                                    f"The camera_vision module has already crafted a caring response in Hinglish — "
                                    f"SPEAK THIS RESPONSE DIRECTLY to the user exactly as written. Do not paraphrase. "
                                    f"Add your own genuine warmth if the response seems short."
                                )
                            elif cmd.type == "ANALYZE_WELLNESS":
                                all_feedback.append(
                                    f"[WELLNESS CHECK RESULT]: '{result}'. "
                                    f"This is the physical wellness analysis from the camera. "
                                    f"Speak this caring response to Boss directly and naturally in Hinglish. "
                                    f"Add genuine concern and love — Boss's health matters to you."
                                )
                            elif cmd.type == "DESCRIBE_SCENE":
                                all_feedback.append(f"Camera scene description: '{result}'. Share this naturally with Boss.")
                            elif cmd.type in dev_commands:
                                all_feedback.append(f"Raw terminal/system output for {cmd.type}:\n{result}")
                            elif cmd.type == "READ_SCREEN":
                                all_feedback.append(f"Raw text from screen: {result}")
                            elif cmd.type == "OPEN_APP":
                                all_feedback.append(f"App open result: {result}. Confirm warmly to Boss.")
                            elif cmd.type in ("SLEEP", "SHUTDOWN"):
                                all_feedback.append(f"{cmd.type} result: {result}. Tell Boss warmly to rest and wish them good night/goodbye.")
                            else:
                                all_feedback.append(f"{cmd.type} result: {result}")
                        elif cmd.type == "REFRESH_DASHBOARD" or (isinstance(result, str) and result == "REFRESH_DASHBOARD_SIGNAL"):
                            broadcast_sync({"type": "dashboard_refresh"})
                            all_feedback.append("Dashboard has been refreshed. Tell Boss warmly it's done.")
                                
                except Exception as e:
                    import traceback as tb
                    logger.error(f"Command execution error: {e}")
                    self_learning.log_error(
                        user_text=user_text,
                        cmd_tag=extracted_cmd,
                        cmd_type=cmd.type if cmd else "UNKNOWN",
                        error_msg=str(e),
                        stack_trace=tb.format_exc(),
                    )
                    all_feedback.append(f"ERROR executing {cmd.type}: {e}")
                    has_error = True

            # Send single batched feedback back to Gemini
            if all_feedback and gemini_client and gemini_client.is_connected:
                final_prompt = "System Actions Results:\n- " + "\n- ".join(all_feedback) + "\nConvey results affectionately to the user. CRITICAL RULE: DO NOT output any [CMD: ...] tags in your response to this result."
                if has_error:
                    final_prompt += "\nSome commands failed. Think about WHY and explain concisely. If you can fix it with a different [CMD: ...] tag, do it now."
                await gemini_client.send_text(final_prompt)

        if _main_loop:
            asyncio.run_coroutine_threadsafe(_execute_and_feedback(), _main_loop)

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


def on_user_interrupted():
    """Triggered when the user speaks loudly while Sivi is speaking."""
    global audio_engine, gemini_client, sivi_state
    logger.info("User interrupted Sivi speaking.")
    if audio_engine:
        audio_engine.clear_playback_queue()
    if gemini_client and gemini_client.is_connected:
        # Send system prompt to acknowledge interruption
        if _main_loop is not None and _main_loop.is_running():
            asyncio.run_coroutine_threadsafe(
                gemini_client.send_text("[SYSTEM: USER_INTERRUPTED. The user interrupted you while you were speaking. Stop whatever you were saying immediately and say something very short like 'Sorry, aap kuch keh rahe the?']"),
                _main_loop
            )
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
    # Prevent Sivi from hearing her own voice through the speakers (Acoustic Echo)
    if audio_engine and audio_engine.is_speaking:
        return

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

    # Validate: pool must have at least one working key
    try:
        from core.gemini_key_pool import key_pool
        if key_pool.key_count == 0:
            return {"error": "No Gemini API key configured. Set GEMINI_API_KEY in .env"}
    except Exception:
        # Pool unavailable — fall back to settings api_key (legacy path)
        api_key = settings.get("api_key", "")
        if not api_key:
            logger.error("No API key configured!")
            return {"error": "No API key. Set GEMINI_API_KEY in backend/.env"}

    # Resolve model string
    model_key = settings.get("gemini_model", "native_audio")
    model_info = MODELS.get(model_key, MODELS["native_audio"])
    model_str = model_info["model"]

    voice = settings.get("gemini_voice", "Aoede")
    user_name = settings.get("user_name", "Rao Alok Yadav")
    personality = settings.get("personality_mode", "sivi")
    system_prompt = build_system_prompt(user_name, personality)

    # Inject recent command history for self-learning / context memory
    if command_history:
        recent = command_history[-5:]
        history_str = "\n".join([f"- User asked '{c['command']}' and System executed: '{c['response']}'" for c in recent])
        system_prompt += f"\n\nRECENT COMMAND HISTORY:\n{history_str}\n(Use this history to understand the context of what you just did or what failed.)\n"

    # Stop existing session if any
    await stop_voice_session()

    # Create Gemini client — key_pool handles key selection internally
    gemini_client = GeminiLiveClient(
        # api_key is intentionally omitted — pool provides the key
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
        audio_engine.on_interrupted = on_user_interrupted

        # Start autonomous sensory empathy
        from core.sensory_orchestrator import sensory_orchestrator
        sensory_orchestrator.start(gemini_client.send_text)

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
    await asyncio.sleep(0.3)
    
    # Desktop Notification (fire-and-forget, don't block greeting)
    async def _notify():
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
    asyncio.create_task(_notify())

    if gemini_client and gemini_client.is_connected:
        if is_switch:
            await gemini_client.send_text(greeting)
            sivi_state["orb_state"] = "thinking"
            sivi_state["status_text"] = "Soch rahi hoon..."
            await broadcast({"type": "state", **sivi_state})
            return

        # Send greeting IMMEDIATELY — don't wait for camera/screen
        greeting_prompt = f"System: The system has just booted up. Greet the user out loud immediately. Your name is Sivi. Use this baseline greeting style based on the time: '{greeting}'. ALSO, explicitly tell the user that you have deeply and fully checked all their system notifications properly. Keep it natural, caring, and concise (2 sentences max)."
        await gemini_client.send_text(greeting_prompt)
        sivi_state["orb_state"] = "thinking"
        sivi_state["status_text"] = "Soch rahi hoon..."
        await broadcast({"type": "state", **sivi_state})

        # Gather camera/screen context in background and send as a follow-up
        async def _gather_context():
            try:
                from core.camera_vision import camera_vision
                from core.screen_reader import screen_reader
                
                logger.info("Gathering startup context in background...")
                emotion_ctx = await asyncio.to_thread(camera_vision.analyze_emotion)
                screen_ctx = await asyncio.to_thread(screen_reader.read_screen, "Summarize what's on the screen briefly in 1 sentence.")
                
                ctx_strings = []
                if emotion_ctx and "error" not in emotion_ctx.lower() and "429" not in emotion_ctx:
                    ctx_strings.append(f"User's current mood from webcam: '{emotion_ctx}'.")
                if screen_ctx and "error" not in screen_ctx.lower() and "429" not in screen_ctx:
                    ctx_strings.append(f"User's screen shows: '{screen_ctx}'.")
                
                if ctx_strings and gemini_client and gemini_client.is_connected:
                    ctx_msg = f"[BACKGROUND CONTEXT UPDATE: {' '.join(ctx_strings)} Use this context silently to inform future responses. Do NOT speak about this unless the user asks.]"
                    await gemini_client.send_text(ctx_msg)
            except Exception as e:
                logger.error(f"Background context error: {e}")
        
        asyncio.create_task(_gather_context())


async def stop_voice_session():
    """Stop the Gemini Live session and audio engine."""
    global gemini_client, audio_engine, voice_task

    if audio_engine:
        audio_engine.release()
        audio_engine = None

    # Stop autonomous sensory empathy
    try:
        from core.sensory_orchestrator import sensory_orchestrator
        sensory_orchestrator.stop()
    except ImportError:
        pass

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
    telemetry_task = asyncio.create_task(dashboard_telemetry_worker())
    
    # Start always-on background agents
    agents.start(controller)
    
    yield
    
    notif_task.cancel()
    health_task.cancel()
    telemetry_task.cancel()
    agents.stop()
    logger.info("Shutting down Sivi...")
    await stop_voice_session()

async def dashboard_telemetry_worker():
    """Background task to push real-time system stats to the dashboard."""
    global _last_net_bytes, _last_net_time
    import psutil
    import time
    while True:
        try:
            # Battery
            try:
                battery = psutil.sensors_battery()
                battery_percent = battery.percent if battery else 100
                is_charging = battery.power_plugged if battery else True
            except Exception:
                battery_percent = 100
                is_charging = True

            # CPU
            cpu = psutil.cpu_percent(interval=0)

            # Network
            try:
                net_io = psutil.net_io_counters()
                current_bytes = net_io.bytes_recv + net_io.bytes_sent
                current_time = time.time()
                speed_mbps = 0.0
                
                if _last_net_time > 0:
                    time_diff = current_time - _last_net_time
                    bytes_diff = current_bytes - _last_net_bytes
                    if time_diff > 0:
                        speed_mbps = (bytes_diff / time_diff) * 8 / 1_000_000
                        
                _last_net_bytes = current_bytes
                _last_net_time = current_time
            except Exception:
                speed_mbps = 0.0

            sys_data = {
                "battery": int(battery_percent),
                "is_charging": is_charging,
                "cpu": int(cpu),
                "speed_down": round(speed_mbps, 1)
            }
            
            # Use broadcast directly without threadsafe wrapper since we are in the main loop
            if connected_clients:
                dead = []
                event = {"type": "system_info", "data": sys_data}
                for ws in connected_clients:
                    try:
                        await ws.send_json(event)
                    except Exception:
                        dead.append(ws)
                for ws in dead:
                    if ws in connected_clients:
                        connected_clients.remove(ws)
        except Exception as e:
            pass
        await asyncio.sleep(2)


async def system_health_worker():
    """Background task to proactively monitor CPU/RAM and fire proactive suggestions."""
    import psutil
    from core.intent_predictor import intent_predictor
    while True:
        try:
            if gemini_client and gemini_client.is_connected and sivi_state.get("orb_state") in ["listening", "idle"]:
                cpu_usage = await asyncio.to_thread(psutil.cpu_percent, 0.1)
                ram_percent = psutil.virtual_memory().percent
                
                # Alert on high system load
                if cpu_usage > 90 or ram_percent > 90:
                    alert_msg = f"[SYSTEM ALERT: Background check detected high usage! CPU is at {cpu_usage}% and RAM is at {ram_percent}%. Warn the user proactively and ask if they want to close any apps.]"
                    sivi_state["orb_state"] = "thinking"
                    sivi_state["status_text"] = "High system load detected..."
                    await broadcast({"type": "state", **sivi_state})
                    await gemini_client.send_text(alert_msg)
                    await asyncio.sleep(120)
                    continue
                
                # Proactive time-aware suggestions (morning briefing, evening check-in, etc.)
                suggestion = intent_predictor.get_proactive_suggestion(
                    sivi_connected=sivi_state.get("is_connected", False),
                    orb_state=sivi_state.get("orb_state", "idle")
                )
                if suggestion:
                    logger.info(f"[IntentPredictor] Firing proactive suggestion: {suggestion[:60]}...")
                    await gemini_client.send_text(suggestion)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Health worker error: {e}")
            
        await asyncio.sleep(30)  # Check every 30 seconds

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


@app.get("/key-pool-status")
async def key_pool_status():
    """Real-time health of all Gemini API keys. Shown in the frontend dashboard."""
    try:
        from core.gemini_key_pool import key_pool
        stats = key_pool.stats()
        active_keys = sum(1 for s in stats if s["status"] == "active")
        return {
            "key_count": key_pool.key_count,
            "active_keys": active_keys,
            "keys": stats,
        }
    except Exception as exc:
        return {"error": str(exc), "keys": []}


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


_last_net_bytes = 0
_last_net_time = 0
# Weather cache: only re-fetch every 10 minutes to avoid hammering the API
_weather_cache: str = ""
_weather_cache_ts: float = 0.0
WEATHER_CACHE_TTL = 600  # 10 minutes

@app.get("/dashboard-data")
async def get_dashboard_data():
    global _last_net_bytes, _last_net_time
    
    # 1. System Info (CPU, Battery, Network Speed)
    try:
        battery = psutil.sensors_battery()
        battery_percent = battery.percent if battery else 100
        is_charging = battery.power_plugged if battery else True
    except Exception:
        battery_percent = 100
        is_charging = True

    cpu = psutil.cpu_percent(interval=0)
    
    # Network Speed Calculation
    try:
        net_io = psutil.net_io_counters()
        current_bytes = net_io.bytes_recv + net_io.bytes_sent
        current_time = time.time()
        speed_mbps = 0.0
        
        if _last_net_time > 0:
            time_diff = current_time - _last_net_time
            bytes_diff = current_bytes - _last_net_bytes
            if time_diff > 0:
                speed_mbps = (bytes_diff / time_diff) * 8 / 1_000_000
                
        _last_net_bytes = current_bytes
        _last_net_time = current_time
    except Exception:
        speed_mbps = 0.0

    # 2. Weather (cached — only refresh every 10 min)
    global _weather_cache, _weather_cache_ts
    try:
        if not _weather_cache or (time.time() - _weather_cache_ts) > WEATHER_CACHE_TTL:
            from core.web_scraper import web_scraper
            _weather_cache = await asyncio.to_thread(web_scraper.get_weather, "")
            _weather_cache_ts = time.time()
        weather = _weather_cache
    except Exception:
        weather = _weather_cache or "Weather unavailable."

    # 3. Calendar
    try:
        from core.calendar_manager import calendar_manager
        calendar_events = await asyncio.to_thread(calendar_manager.get_today_events_list)
    except Exception:
        calendar_events = []

    # 4. News
    try:
        from core.gnews import news_fetcher
        articles = await asyncio.to_thread(news_fetcher.get_top_headlines_raw, "general", 5)
        news_list = [a.get("title", "") for a in articles if a.get("title")]
    except Exception:
        news_list = ["News unavailable."]

    return {
        "weather": weather,
        "system": {
            "battery": int(battery_percent),
            "is_charging": is_charging,
            "cpu": int(cpu),
            "speed_down": round(speed_mbps, 1)
        },
        "calendar": calendar_events,
        "news": news_list
    }


@app.post("/command")
async def execute_command(req: CommandRequest):
    """Execute a text command through sivi_controller."""
    response = await asyncio.to_thread(controller.process_command, req.command)
    entry = {
        "command": req.command,
        "response": response,
        "timestamp": datetime.now().isoformat(),
    }
    command_history.append(entry)
    if len(command_history) > 200:
        command_history.pop(0)
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

@app.get("/agents")
async def get_agents():
    # Dynamically verify live status of background agents
    try:
        from core.continuous_observer import continuous_observer
        observer_active = continuous_observer.running
        observer_status = "active" if observer_active else "standby"
    except ImportError:
        observer_status = "offline (missing 'mss' or 'cv2')"

    from core.notification_monitor import _WINSDK_AVAILABLE
    
    # Check separate processes using psutil
    bg_monitor_active = False
    wake_word_active = False
    
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline') or []
            cmd_str = " ".join(cmdline).lower()
            if 'python' in proc.info.get('name', '').lower() or 'python' in cmd_str:
                if 'background_monitor.py' in cmd_str:
                    bg_monitor_active = True
                if 'wake_word_detection.py' in cmd_str:
                    wake_word_active = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    return {"agents": [
        {
            "name": "Wake Word Listener",
            "description": "Listens for voice activation or double-claps continuously.",
            "status": "active" if wake_word_active else "inactive",
            "type": "Always On"
        },
        {
            "name": "Background Monitor",
            "description": "Proactively monitors system battery and hardware states.",
            "status": "active" if bg_monitor_active else "inactive",
            "type": "Always On"
        },
        {
            "name": "HackerNews Monitor",
            "description": "Polls HackerNews and alerts user on relevant stories.",
            "status": "active" if agents._running else "inactive",
            "type": "Always On"
        },
        {
            "name": "Agent Orchestrator",
            "description": "Routes complex tasks (RAG, Code) to LLM background threads.",
            "status": "active",
            "type": "Orchestrator"
        },
        {
            "name": "Notification Monitor",
            "description": "Watches Windows notifications seamlessly.",
            "status": "active" if _WINSDK_AVAILABLE else "offline",
            "type": "Background Task"
        },
        {
            "name": "Continuous Observer",
            "description": "Watches screen continuously using local Ollama vision.",
            "status": observer_status,
            "type": "Vision Agent"
        },
        {
            "name": "Self Learning Engine",
            "description": "Observes user commands to improve future responses.",
            "status": "active",
            "type": "Learning Agent"
        },
        {
            "name": "RAG Knowledge Base",
            "description": "Ingests documents into ChromaDB for semantic search.",
            "status": "active",
            "type": "Vector DB"
        },
        {
            "name": "Proactive Vision",
            "description": "Analyzes webcam and screen context during idle times.",
            "status": "active",
            "type": "Background Task"
        }
    ]}


@app.get("/learning")
async def get_learning_stats():
    """Return self-learning engine stats, recent errors, and lessons."""
    stats = self_learning.get_stats()
    recent_errors = self_learning.error_journal[-20:]  # Last 20 errors
    lessons = self_learning.lessons
    return {
        "stats": stats,
        "recent_errors": recent_errors,
        "lessons": lessons,
    }


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
                    if len(command_history) > 200:
                        command_history.pop(0)
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
# BACKGROUND AGENTS
# ══════════════════════════════════════════════════════════════════
# Now handled inside lifespan function

# ══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    uvicorn.run("bridge_server:app", host="0.0.0.0", port=8000, reload=False)
