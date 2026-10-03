"""
SIVI AI — Sivi Controller (The Brain)
Parses all commands and routes them to the correct module.
"""

import os
import sys
import threading

_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
if _CORE_DIR not in sys.path:
    sys.path.insert(0, _CORE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(_CORE_DIR, "..", ".env"))

from app_launcher import app_launcher
from system_controller import system_controller
from window_manager import window_manager
from keyboard_controller import keyboard_controller
from mouse_controller import mouse_controller
from screen_reader import screen_reader
from window_reader import window_reader
from file_manager import file_manager
from hindi_voice import hindi_voice
from command_parser import parse_command, PCCommand
from system_monitor import system_monitor
from memory_vault import memory_vault
from dev_tools import dev_tools
from web_scraper import web_scraper
from log_detective import log_detective
from task_queue import task_queue
from database_whisperer import database_whisperer
from knowledge_graph import knowledge_graph
from git_orchestrator import git_orchestrator
from swarm_manager import swarm_manager
from mobile_handoff import mobile_handoff
try:
    from uia_controller import uia_controller
    _uia_available = True
except Exception as e:
    _uia_available = False
    print(f" uia_controller unavailable: {e}")

try:
    from camera_vision import camera_vision
    _camera_available = True
except Exception as e:
    _camera_available = False
    print(f" camera_vision unavailable: {e}")

try:
    from browser_controller import browser_controller
    _browser_available = True
except Exception as e:
    _browser_available = False
    print(f" browser_controller unavailable: {e}")


try:
    from gnews import news_fetcher
    _news_available = True
except Exception as e:
    _news_available = False

try:
    from whatsapp_web_controller import whatsapp_web_controller
    _whatsapp_available = True
except Exception as e:
    _whatsapp_available = False

try:
    from spotify_controller import spotify_controller
    _spotify_available = True
except Exception as e:
    _spotify_available = False

try:
    from local_llm import local_llm
    _local_llm_available = True
except Exception as e:
    _local_llm_available = False


try:
    from calendar_manager import calendar_manager
    _calendar_available = True
except Exception as e:
    _calendar_available = False


class SiviController:
    def __init__(self):
        self.history: list[str] = []
        self._timers: dict[str, threading.Timer] = {}

    def get_module_status(self) -> list[dict]:
        return [
            {"name": "App Launcher",        "file": "app_launcher.py",       "status": "active"},
            {"name": "System Controller",   "file": "system_controller.py",  "status": "active"},
            {"name": "Window Manager",      "file": "window_manager.py",     "status": "active"},
            {"name": "Keyboard Controller", "file": "keyboard_controller.py","status": "active"},
            {"name": "Camera Vision",       "file": "camera_vision.py",      "status": "active" if _camera_available else "no-key"},
            {"name": "News",                "file": "gnews.py",              "status": "active" if _news_available else "no-key"},
            {"name": "WhatsApp Web",    "file": "whatsapp_web_controller.py",  "status": "active" if _whatsapp_available else "not-configured"},
            {"name": "Screen Reader",       "file": "screen_reader.py",      "status": "active"},
            {"name": "File Manager",        "file": "file_manager.py",       "status": "active"},
            {"name": "Hindi Voice",         "file": "hindi_voice.py",        "status": "active"},
            {"name": "Spotify",             "file": "spotify_controller.py", "status": "active" if _spotify_available else "not-configured"},
            {"name": "Local LLM",           "file": "local_llm.py",          "status": "active" if _local_llm_available else "not-configured"},
            {"name": "Calendar",            "file": "calendar_manager.py",   "status": "active" if _calendar_available else "not-configured"},
            {"name": "System Monitor",      "file": "system_monitor.py",     "status": "active"},
            {"name": "Memory Vault",        "file": "memory_vault.py",       "status": "active"},
            {"name": "Developer Tools",     "file": "dev_tools.py",          "status": "active"},
            {"name": "Browser Controller",  "file": "browser_controller.py", "status": "active" if _browser_available else "not-configured"},
        ]

    def process_command(self, text: str) -> str:
        print(f"\n Brain received command: '{text}'")
        text_lower = text.lower().strip()
        self.history.append(text_lower)

        translated = hindi_voice.try_translate(text_lower)
        if translated != text_lower:
            print(f"    Hindi detected, translated: '{translated}'")
            text_lower = translated

        cmd = parse_command(text_lower)
        if not cmd:
            if _local_llm_available and ("use local ai" in text_lower or "use cloud ai" in text_lower):
                return local_llm.switch_mode(text_lower)
            return "Command not recognized. Try 'open notepad', 'play music', 'news', or 'take photo'."

        return self.execute_command(cmd)

    def execute_command(self, cmd: PCCommand) -> str:
        t = cmd.type
        p = cmd.params

        try:
            # ── App control ──────────────────────────────────────
            if t == "OPEN_APP":   return app_launcher.launch_app(p.get("raw") or p.get("app_name"))
            if t == "CLOSE_APP":  return window_manager.close_window(p.get("app_name"))
            if t == "SWITCH_APP": return window_manager.focus_window(p.get("app_name"))

            # ── Browser Tabs ─────────────────────────────────────
            if t == "TAB_NEW":    return browser_controller.manage_tabs("new") if _browser_available else keyboard_controller.press_key("new tab")
            if t == "TAB_CLOSE":  return browser_controller.manage_tabs("close") if _browser_available else keyboard_controller.press_key("close tab")
            if t == "TAB_NEXT":   return browser_controller.manage_tabs("next") if _browser_available else keyboard_controller.press_key("next tab")
            if t == "TAB_PREV":   return browser_controller.manage_tabs("prev") if _browser_available else keyboard_controller.press_key("previous tab")

            # ── Media / YouTube / Spotify ─────────────────────────
            if t == "PLAY_YOUTUBE": return browser_controller.play_youtube(p.get("query")) if _browser_available else app_launcher.play_on_youtube(p.get("query"))
            if t == "PLAY_SPOTIFY":
                return spotify_controller.handle_command("spotify play " + p.get("query", "")) if _spotify_available else "Spotify is not configured."

            # ── Search ────────────────────────────────────────────
            if t == "SEARCH": return browser_controller.search_google(p.get("query")) if _browser_available else app_launcher.google_search(p.get("query"))

            # ── Keyboard ──────────────────────────────────────────
            if t == "TYPE_TEXT": return keyboard_controller.type_text(p.get("text"))
            if t == "PRESS_KEY": return keyboard_controller.press_key(p.get("key"))

            # ── UIA / Native Accessibility ────────────────────────
            if t == "UIA_CLICK":
                return uia_controller.click_element(p.get("app_name"), p.get("element_name")) if _uia_available else "UIA module unavailable."
            if t == "UIA_TYPE":
                return uia_controller.type_into_element(p.get("app_name"), p.get("element_name"), p.get("text")) if _uia_available else "UIA module unavailable."
            if t == "UIA_READ":
                return uia_controller.read_window_content(p.get("app_name")) if _uia_available else "UIA module unavailable."

            # ── Mouse ─────────────────────────────────────────────

            if t == "MOUSE_CLICK":
                return mouse_controller.click(button=p.get("button", "left"), double=p.get("double", False))
            if t == "MOUSE_SCROLL":
                return mouse_controller.scroll(500 if p.get("direction") == "up" else -500)
            if t == "MOUSE_MOVE":
                amt = p.get("amount", 200)
                d = p.get("direction")
                if d == "up":    return mouse_controller.move_by(0, -amt)
                if d == "down":  return mouse_controller.move_by(0, amt)
                if d == "left":  return mouse_controller.move_by(-amt, 0)
                return mouse_controller.move_by(amt, 0)
            if t == "MOUSE_MOVE_TO":
                return mouse_controller.move_to(p.get("x", 0), p.get("y", 0))

            # ── Volume ────────────────────────────────────────────
            if t == "VOLUME_UP":   return system_controller.volume_up()
            if t == "VOLUME_DOWN": return system_controller.volume_down()
            if t == "MUTE":        return system_controller.mute_volume()
            if t == "VOLUME_SET":
                return system_controller.set_volume(p.get("level", 50))

            # ── Power ─────────────────────────────────────────────
            if t == "LOCK_SCREEN": return system_controller.lock_screen()
            if t == "SHUTDOWN":    return system_controller.shutdown()
            if t == "RESTART":     return system_controller.restart()
            if t == "SLEEP":       return system_controller.sleep_mode()

            # ── Brightness ────────────────────────────────────────
            if t == "BRIGHTNESS_UP":   return system_controller.brightness_up()
            if t == "BRIGHTNESS_DOWN": return system_controller.brightness_down()

            # ── Window management ─────────────────────────────────
            if t == "MINIMIZE_WINDOW": return window_manager.minimize_window(p.get("app_name"))
            if t == "MAXIMIZE_WINDOW": return window_manager.maximize_window(p.get("app_name"))
            if t == "SNAP_LEFT":  return window_manager.snap_left()
            if t == "SNAP_RIGHT": return window_manager.snap_right()
            if t == "READ_WINDOWS": return window_reader.get_active_windows()

            # ── Screen ────────────────────────────────────────────
            if t == "READ_SCREEN": return screen_reader.read_screen("read my screen")
            if t == "SCREENSHOT":  return system_controller.take_screenshot()

            # ── Connectivity ──────────────────────────────────────
            if t == "WIFI_ON":        return system_controller.wifi_on()
            if t == "WIFI_OFF":       return system_controller.wifi_off()
            if t == "BLUETOOTH_ON":   return system_controller.bluetooth_on()
            if t == "BLUETOOTH_OFF":  return system_controller.bluetooth_off()

            # ── Media keys ────────────────────────────────────────
            if t == "MEDIA_PLAY_PAUSE": return system_controller.media_play_pause()
            if t == "MEDIA_NEXT":       return system_controller.media_next()
            if t == "MEDIA_PREV":       return system_controller.media_prev()

            # ── Clipboard ─────────────────────────────────────────
            if t == "READ_CLIPBOARD":  return system_controller.read_clipboard()
            if t == "WRITE_CLIPBOARD": return system_controller.write_clipboard(p.get("text"))

            # ── News ──────────────────────────────────────────────
            if t == "NEWS":
                return news_fetcher.get_top_headlines() if _news_available else "News module offline. Check your GNews API key."

            # ── Calendar ──────────────────────────────────────────
            if t == "CALENDAR_EVENTS":
                return calendar_manager.get_today_events() if _calendar_available else "Calendar is offline."
            if t == "CREATE_EVENT":
                if not p.get("title"): return "What event would you like to schedule?"
                return calendar_manager.quick_add_event(p.get("title")) if _calendar_available else "Calendar offline."

            # ── WhatsApp ──────────────────────────────────
            if t == "SEND_WHATSAPP":
                if not p.get("number"): return "Format: 'send message to NUMBER saying TEXT'"
                return whatsapp_web_controller.send_whatsapp_message(p.get("number"), p.get("content")) if _whatsapp_available else "WhatsApp offline."
            if t == "WHATSAPP_READ_CHAT":
                return whatsapp_web_controller.read_chat(contact=p.get("contact", "")) if _whatsapp_available else "WhatsApp offline."
            if t == "WHATSAPP_CALL":
                if not p.get("number"): return "Please specify the contact number to call."
                return whatsapp_web_controller.voice_video_call(p.get("number"), p.get("call_type")) if hasattr(whatsapp_web_controller, 'voice_video_call') else "Not supported in Web."
            if t == "WHATSAPP_SEND_MEDIA":
                if not p.get("number") or not p.get("filepath"): return "Please specify number and file path."
                return whatsapp_web_controller.send_media(p.get("number"), p.get("filepath")) if hasattr(whatsapp_web_controller, 'send_media') else "Not supported in Web."
            if t == "WHATSAPP_VOICE_NOTE":
                if not p.get("number"): return "Please specify the contact to send the voice note to."
                return whatsapp_web_controller.record_voice_note(p.get("number")) if hasattr(whatsapp_web_controller, 'record_voice_note') else "Not supported in Web."

            # ── Advanced Browser Controls ─────────────────────────
            if t == "BROWSER_READ_PAGE": return browser_controller.read_current_page() if _browser_available else "Browser offline."
            if t == "BROWSER_SCROLL":    return browser_controller.scroll(p.get("direction", "down")) if _browser_available else "Browser offline."
            if t == "BROWSER_FULLSCREEN":return browser_controller.toggle_fullscreen() if _browser_available else "Browser offline."
            if t == "BROWSER_STATUS":    return browser_controller.list_tabs() if _browser_available else "Browser offline."

            # ── Files ─────────────────────────────────────────────
            if t == "CREATE_FILE":   return file_manager.create_file(p.get("name"))
            if t == "CREATE_FOLDER": return file_manager.create_folder(p.get("name"))
            if t == "DELETE_FILE":   return file_manager.delete_file(p.get("name"))
            if t == "DELETE_FOLDER": return file_manager.delete_file(p.get("name"))
            if t == "FIND_FILE":     return file_manager.find_file(p.get("name"))
            if t == "LIST_FILES":    return file_manager.list_files(p.get("folder"))
            if t == "OPEN_FILE":     return file_manager.open_file(p.get("name"))

            # ── System Status / Memory / Weather ────────────────────────────
            if t == "SYSTEM_STATUS": return system_monitor.get_system_status()
            if t == "GET_WEATHER":   return web_scraper.get_weather(p.get("location", ""))
            if t == "REMEMBER":  return memory_vault.remember(p.get("fact"))
            if t == "FORGET_ALL": return memory_vault.forget_all()
            if t == "GRAPH_ADD": return knowledge_graph.add_relation(p.get("subject"), p.get("predicate"), p.get("object"))
            if t == "GRAPH_QUERY": return knowledge_graph.query_entity(p.get("entity"))
            
            if t == "SWARM_RUN":
                return swarm_manager.delegate_research(p.get("query"))
            if t == "MOBILE_HANDOFF":
                return mobile_handoff.send_to_mobile(p.get("message"))

            # ── Camera / Vision ───────────────────────────────────
            if t == "ANALYZE_EMOTION":
                return camera_vision.analyze_emotion() if _camera_available else "Camera module offline hai Boss. Webcam se mood nahi dekh sakti abhi."
            if t == "ANALYZE_WELLNESS":
                return camera_vision.analyze_wellness() if _camera_available else "Wellness check ke liye webcam chahiye Boss, abhi offline hai."
            if t == "DESCRIBE_SCENE":
                return camera_vision.describe_scene() if _camera_available else "Camera module offline."

            # ── Timer & Scheduling ────────────────────────────────
            if t == "SET_TIMER":
                return self._set_timer(p.get("seconds", 60), p.get("label", "Timer"))
            if t == "SCHEDULE_TASK":
                return task_queue.schedule_task(p.get("command"), p.get("instruction"), p.get("delay", 60))
            if t == "LIST_SCHEDULED_TASKS":
                return task_queue.list_pending_tasks()

            # ── Developer Tools ───────────────────────────────────
            if t == "DEV_RUN_CMD":      return dev_tools.run_command(p.get("command"))
            if t == "DEV_GIT_STATUS":   return dev_tools.get_git_status()
            if t == "DEV_GIT_COMMIT":   return git_orchestrator.commit_and_push(p.get("message"))
            if t == "DEV_RUN_TESTS":    return git_orchestrator.run_test_suite(p.get("cmd"))
            if t == "DEV_KILL_PORT":    return dev_tools.kill_port(p.get("port"))
            if t == "DEV_ANALYZE_CODE": return dev_tools.analyze_code(p.get("filename"))
            if t == "DEV_GENERATE_CODE": return dev_tools.generate_code(p.get("filename"), p.get("instructions"))
            if t == "DEV_EXECUTE_SCRIPT":return dev_tools.execute_python_script(p.get("goal"))
            if t == "DEV_SPAWN_SUBAGENT":return dev_tools.spawn_subagent(p.get("goal"))
            if t == "DEV_OPEN_EDITOR":  return dev_tools.open_in_editor(p.get("filename"))
            if t == "DEV_CLOSE_EDITOR": return dev_tools.close_current_file()

            if t == "DEV_MONITOR_LOGS": return log_detective.start_monitoring(p.get("filename"))
            if t == "DEV_DB_QUERY":     return database_whisperer.execute_read_query(p.get("connection_string"), p.get("query"))

            # ── MCP Routing ───────────────────────────────────────
            if t == "MCP_CALL":
                from mcp_router import mcp_router
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # We're in a thread via asyncio.to_thread; use run_coroutine_threadsafe
                        future = asyncio.run_coroutine_threadsafe(
                            mcp_router.call_tool(p.get("server"), p.get("tool"), p.get("args")),
                            loop
                        )
                        return future.result(timeout=30)
                    else:
                        return loop.run_until_complete(mcp_router.call_tool(p.get("server"), p.get("tool"), p.get("args")))
                except Exception as e:
                    return f"MCP call failed: {e}"

            # ── Phase 1 & 2 System Commands ───────────────────────
            if t == "PROCESS_KILL":     return system_controller.kill_process(p.get("process_name"))
            if t == "PROCESS_LIST":     return system_controller.list_processes()
            if t == "DISK_INFO":        return system_controller.get_disk_info()
            if t == "IP_ADDRESS":       return system_controller.get_network_info()
            if t == "PING":             return system_controller.ping_host(p.get("host"))
            if t == "EMPTY_RECYCLE":    return system_controller.empty_recycle_bin()
            if t == "NETWORK_STATUS":   return system_controller.get_network_info()
            if t == "SYSTEM_UPTIME":    return system_controller.get_system_uptime()

            # ── Dashboard Refresh ─────────────────────────────────
            if t == "REFRESH_DASHBOARD":
                return "REFRESH_DASHBOARD_SIGNAL"

            return f"Command '{t}' is not fully mapped in the controller."

        except Exception as e:
            import traceback
            print(f"CRITICAL MODULE ERROR:\n{traceback.format_exc()}")
            return f"SYSTEM_ERROR: Command execution failed: {e}"

    def _set_timer(self, seconds: int, label: str) -> str:
        """Set a non-blocking timer that fires after `seconds`."""
        def _fire():
            print(f"\n⏰ TIMER FIRED: {label}")
            try:
                from plyer import notification
                notification.notify(title="⏰ SIVI Timer", message=f"{label} timer is done!", timeout=10)
            except Exception as e:
                pass
            # Send a system tray beep as fallback
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)

        if label in self._timers:
            self._timers[label].cancel()

        t = threading.Timer(seconds, _fire)
        t.daemon = True
        t.start()
        self._timers[label] = t

        mins = seconds // 60
        secs = seconds % 60
        if mins > 0:
            time_str = f"{mins} minute{'s' if mins > 1 else ''}" + (f" {secs} seconds" if secs else "")
        else:
            time_str = f"{secs} second{'s' if secs > 1 else ''}"
        return f"Timer set for {time_str}. I will notify you when it's done!"


# Singleton instance
controller = SiviController()
