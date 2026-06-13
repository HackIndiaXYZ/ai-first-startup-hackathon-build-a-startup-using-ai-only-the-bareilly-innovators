"""
TITAN AI — Jarvis Controller (The Brain)
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
    from medical import medical_assistant
    _medical_available = True
except Exception as e:
    _medical_available = False

try:
    from jarvis_email import email_manager
    _email_available = True
except Exception as e:
    _email_available = False

try:
    from gnews import news_fetcher
    _news_available = True
except Exception as e:
    _news_available = False

try:
    from whatsapp_desktop_controller import whatsapp_desktop_controller
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
    from plugin_manager import plugin_manager
    _plugins_available = True
except Exception as e:
    _plugins_available = False

try:
    from calendar_manager import calendar_manager
    _calendar_available = True
except Exception as e:
    _calendar_available = False


class JarvisController:
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
            {"name": "Medical AI",          "file": "medical.py",            "status": "active" if _medical_available else "no-key"},
            {"name": "Email",               "file": "jarvis_email.py",       "status": "active" if _email_available else "no-key"},
            {"name": "News",                "file": "gnews.py",              "status": "active" if _news_available else "no-key"},
            {"name": "WhatsApp Desktop",    "file": "whatsapp_desktop_controller.py",  "status": "active" if _whatsapp_available else "not-configured"},
            {"name": "Screen Reader",       "file": "screen_reader.py",      "status": "active"},
            {"name": "File Manager",        "file": "file_manager.py",       "status": "active"},
            {"name": "Hindi Voice",         "file": "hindi_voice.py",        "status": "active"},
            {"name": "Spotify",             "file": "spotify_controller.py", "status": "active" if _spotify_available else "not-configured"},
            {"name": "Local LLM",           "file": "local_llm.py",          "status": "active" if _local_llm_available else "not-configured"},
            {"name": "Plugin System",       "file": "plugin_manager.py",     "status": "active" if _plugins_available else "not-configured"},
            {"name": "Calendar",            "file": "calendar_manager.py",   "status": "active" if _calendar_available else "not-configured"},
            {"name": "Custom Wake Word",    "file": "custom_wake_word.py",   "status": "active"},
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

        if _plugins_available:
            plugin_result = plugin_manager.try_handle(text_lower)
            if plugin_result:
                return plugin_result

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
                return calendar_manager.create_event(p.get("title")) if _calendar_available else "Calendar offline."

            # ── Medical ───────────────────────────────────────────
            if t == "MEDICAL_ADVICE":
                return medical_assistant.get_advice(p.get("query")) if _medical_available else "Medical AI offline."

            # ── Email / WhatsApp ──────────────────────────────────
            if t == "SEND_EMAIL":
                if not p.get("to"): return "Format: 'send email to NAME saying MESSAGE'"
                return email_manager.send_email(f"{p.get('to')}@gmail.com", "Message from Sivi", p.get("content")) if _email_available else "Email offline."
            if t == "SEND_WHATSAPP":
                if not p.get("number"): return "Format: 'send message to NUMBER saying TEXT'"
                return whatsapp_desktop_controller.send_whatsapp_message(p.get("number"), p.get("content")) if _whatsapp_available else "WhatsApp offline."
            if t == "WHATSAPP_READ_CHAT":
                return whatsapp_desktop_controller.read_chat(contact=p.get("contact", "")) if _whatsapp_available else "WhatsApp offline."
            if t == "WHATSAPP_CALL":
                if not p.get("number"): return "Please specify the contact number to call."
                return whatsapp_desktop_controller.voice_video_call(p.get("number"), p.get("call_type")) if _whatsapp_available else "WhatsApp offline."
            if t == "WHATSAPP_SEND_MEDIA":
                if not p.get("number") or not p.get("filepath"): return "Please specify number and file path."
                return whatsapp_desktop_controller.send_media(p.get("number"), p.get("filepath")) if _whatsapp_available else "WhatsApp offline."
            if t == "WHATSAPP_VOICE_NOTE":
                if not p.get("number"): return "Please specify the contact to send the voice note to."
                return whatsapp_desktop_controller.record_voice_note(p.get("number")) if _whatsapp_available else "WhatsApp offline."

            # ── Advanced Browser Controls ─────────────────────────
            if t == "BROWSER_READ_PAGE": return browser_controller.read_current_page() if _browser_available else "Browser offline."
            if t == "BROWSER_SCROLL":    return browser_controller.scroll(p.get("direction", "down")) if _browser_available else "Browser offline."
            if t == "BROWSER_FULLSCREEN":return browser_controller.toggle_fullscreen() if _browser_available else "Browser offline."

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
            if t == "GET_WEATHER":   return web_scraper.get_weather(p.get("location", "Delhi"))
            if t == "REMEMBER":  return memory_vault.remember(p.get("fact"))
            if t == "FORGET_ALL": return memory_vault.forget_all()

            # ── Camera / Vision ───────────────────────────────────
            if t == "ANALYZE_EMOTION":
                return camera_vision.analyze_emotion() if _camera_available else "Camera module offline."
            if t == "DESCRIBE_SCENE":
                return camera_vision.describe_scene() if _camera_available else "Camera module offline."

            # ── Timer ─────────────────────────────────────────────
            if t == "SET_TIMER":
                return self._set_timer(p.get("seconds", 60), p.get("label", "Timer"))

            # ── Developer Tools ───────────────────────────────────
            if t == "DEV_RUN_CMD":      return dev_tools.run_command(p.get("command"))
            if t == "DEV_GIT_STATUS":   return dev_tools.get_git_status()
            if t == "DEV_KILL_PORT":    return dev_tools.kill_port(p.get("port"))
            if t == "DEV_ANALYZE_CODE": return dev_tools.analyze_code(p.get("filename"))
            if t == "DEV_GENERATE_CODE": return dev_tools.generate_code(p.get("filename"), p.get("instructions"))
            if t == "DEV_EXECUTE_SCRIPT":return dev_tools.execute_python_script(p.get("goal"))
            if t == "DEV_SPAWN_SUBAGENT":return dev_tools.spawn_subagent(p.get("goal"))
            if t == "DEV_OPEN_EDITOR":  return dev_tools.open_in_editor(p.get("filename"))
            if t == "DEV_CLOSE_EDITOR": return dev_tools.close_current_file()

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
                notification.notify(title="⏰ TITAN Timer", message=f"{label} timer is done!", timeout=10)
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
controller = JarvisController()
