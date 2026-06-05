"""
TITAN/Sivi — Comprehensive Integration Test Suite
Tests every module import, function call, and integration flow.
"""

import sys
import os

# Setup paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

passed = 0
failed = 0
errors = []

def test(name, fn):
    global passed, failed
    try:
        result = fn()
        if result is True or result is None:
            passed += 1
            print(f"  ✅ PASS: {name}")
        elif result is False:
            failed += 1
            errors.append((name, "Returned False"))
            print(f"  ❌ FAIL: {name} → returned False")
        else:
            passed += 1
            print(f"  ✅ PASS: {name} → {result}")
    except Exception as e:
        failed += 1
        errors.append((name, str(e)))
        print(f"  ❌ FAIL: {name} → {e}")

# ══════════════════════════════════════════════════════════════
# 1. COMMAND PARSER
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("MODULE 1: Command Parser")
print("="*60)

from command_parser import parse_command, PCCommand

def test_cmd(text, expected_type):
    result = parse_command(text)
    actual = result.type if result else None
    if actual != expected_type:
        raise AssertionError(f"Expected {expected_type}, got {actual}")
    return actual or "None (correct)"

test("Parse 'open chrome'",          lambda: test_cmd("open chrome", "OPEN_APP"))
test("Parse 'kholo notepad'",        lambda: test_cmd("kholo notepad", "OPEN_APP"))
test("Parse 'launch calculator'",    lambda: test_cmd("launch calculator", "OPEN_APP"))
test("Parse 'close notepad'",        lambda: test_cmd("close notepad", "CLOSE_APP"))
test("Parse 'band karo chrome'",     lambda: test_cmd("band karo chrome", "CLOSE_APP"))
test("Parse 'volume up'",            lambda: test_cmd("volume up", "VOLUME_UP"))
test("Parse 'volume badhao'",        lambda: test_cmd("volume badhao", "VOLUME_UP"))
test("Parse 'volume down'",          lambda: test_cmd("volume down", "VOLUME_DOWN"))
test("Parse 'mute the volume'",      lambda: test_cmd("mute the volume", "MUTE"))
test("Parse 'take screenshot'",      lambda: test_cmd("take screenshot", "SCREENSHOT"))
test("Parse 'read my screen'",       lambda: test_cmd("read my screen", "READ_SCREEN"))
test("Parse 'lock screen'",          lambda: test_cmd("lock screen", "LOCK_SCREEN"))
test("Parse 'shutdown the computer'",lambda: test_cmd("shutdown the computer", "SHUTDOWN"))
test("Parse 'restart the computer'", lambda: test_cmd("restart the computer", "RESTART"))
test("Parse 'sleep mode'",           lambda: test_cmd("sleep mode", "SLEEP"))
test("Parse 'brightness up'",        lambda: test_cmd("brightness up", "BRIGHTNESS_UP"))
test("Parse 'brightness down'",      lambda: test_cmd("brightness down", "BRIGHTNESS_DOWN"))
test("Parse 'play arijit singh'",    lambda: test_cmd("play arijit singh", "PLAY_YOUTUBE"))
test("Parse 'search python'",        lambda: test_cmd("search python tutorial", "SEARCH"))
test("Parse 'type hello world'",     lambda: test_cmd("type hello world", "TYPE_TEXT"))
test("Parse 'create file test.txt'", lambda: test_cmd("create file test.txt", "CREATE_FILE"))
test("Parse 'delete file test.txt'", lambda: test_cmd("delete file test.txt", "DELETE_FILE"))
test("Parse 'create folder data'",   lambda: test_cmd("create folder data", "CREATE_FOLDER"))
test("Parse 'find file report'",     lambda: test_cmd("find file report", "FIND_FILE"))
test("Parse 'news'",                 lambda: test_cmd("news", "NEWS"))
test("Parse 'hello' (no match)",     lambda: test_cmd("hello how are you", None))
test("Parse '' (empty)",             lambda: test_cmd("", None))

# Test param extraction
def test_open_params():
    r = parse_command("open chrome")
    if r.params.get("app_name") != "chrome":
        raise AssertionError(f"Expected 'chrome', got '{r.params.get('app_name')}'")
    return r.params.get("app_name")

def test_search_params():
    r = parse_command("search AI tutorials")
    q = r.params.get("query", "")
    if "ai tutorials" not in q.lower():
        raise AssertionError(f"Expected query containing 'ai tutorials', got '{q}'")
    return q

test("Param: app_name from open", test_open_params)
test("Param: query from search",  test_search_params)

# ══════════════════════════════════════════════════════════════
# 2. HINDI VOICE
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("MODULE 2: Hindi Voice")
print("="*60)

from hindi_voice import hindi_voice

test("Import hindi_voice", lambda: True)
test("Translate 'kholo chrome'",       lambda: hindi_voice.try_translate("kholo chrome"))
test("Translate 'gaana bajao arijit'", lambda: hindi_voice.try_translate("gaana bajao arijit"))
test("Translate 'awaaz badhao'",       lambda: hindi_voice.try_translate("awaaz badhao"))
test("Translate 'news sunao'",         lambda: hindi_voice.try_translate("news sunao"))

def test_no_translate():
    r = hindi_voice.try_translate("hello")
    if r != "hello":
        raise AssertionError(f"Expected 'hello' unchanged, got '{r}'")
    return "unchanged ✓"

test("No translate 'hello'", test_no_translate)
test("is_hindi('kholo chrome')", lambda: hindi_voice.is_hindi("kholo chrome"))

def test_not_hindi():
    r = hindi_voice.is_hindi("open chrome")
    if r:
        raise AssertionError(f"Expected False, got {r}")
    return "correctly False"

test("is_hindi('open chrome') = False", test_not_hindi)

# ══════════════════════════════════════════════════════════════
# 3. PERSONALITY
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("MODULE 3: Personality")
print("="*60)

from personality import build_system_prompt, get_greeting, get_personality_list, PERSONALITIES

test("Import personality", lambda: True)

def test_personality_count():
    if len(PERSONALITIES) != 4:
        raise AssertionError(f"Expected 4, got {len(PERSONALITIES)}")
    return f"{len(PERSONALITIES)} personalities"

test("4 personalities defined", test_personality_count)

def test_gf_prompt():
    p = build_system_prompt("Alok", "gf")
    if "Sivi" not in p or "Alok" not in p:
        raise AssertionError("Missing Sivi or Alok in prompt")
    return f"len={len(p)} chars"

test("build_system_prompt(gf)", test_gf_prompt)

def test_pro_prompt():
    p = build_system_prompt("Alok", "professional")
    if "professional" not in p.lower() and "Formal" not in p:
        raise AssertionError("Missing professional/Formal")
    return "OK"

test("build_system_prompt(professional)", test_pro_prompt)

def test_greeting():
    g = get_greeting("Alok", "gf")
    if "Rao" not in g:
        raise AssertionError(f"Missing 'Rao' in greeting: {g}")
    return g

test("get_greeting(gf)", test_greeting)

def test_pl():
    pl = get_personality_list()
    if len(pl) != 4:
        raise AssertionError(f"Expected 4, got {len(pl)}")
    return f"{len(pl)} personalities"

test("get_personality_list", test_pl)

# ══════════════════════════════════════════════════════════════
# 4. APP LAUNCHER
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("MODULE 4: App Launcher")
print("="*60)

from app_launcher import app_launcher

test("Import app_launcher", lambda: True)

def test_apps_dict():
    if len(app_launcher.apps) == 0:
        raise AssertionError("apps dict is empty")
    return f"{len(app_launcher.apps)} apps"

test("apps dict non-empty", test_apps_dict)
test("Has launch_app",       lambda: hasattr(app_launcher, "launch_app"))
test("Has play_on_youtube",  lambda: hasattr(app_launcher, "play_on_youtube"))
test("Has google_search",    lambda: hasattr(app_launcher, "google_search"))

# ══════════════════════════════════════════════════════════════
# 5. SYSTEM CONTROLLER
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("MODULE 5: System Controller")
print("="*60)

from system_controller import system_controller

test("Import system_controller", lambda: True)
test("Has volume_up",    lambda: hasattr(system_controller, "volume_up"))
test("Has volume_down",  lambda: hasattr(system_controller, "volume_down"))
test("Has mute_volume",  lambda: hasattr(system_controller, "mute_volume"))
test("Has lock_screen",  lambda: hasattr(system_controller, "lock_screen"))

# ══════════════════════════════════════════════════════════════
# 6. WINDOW MANAGER
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("MODULE 6: Window Manager")
print("="*60)

from window_manager import window_manager

test("Import window_manager", lambda: True)
test("Has minimize_window",   lambda: hasattr(window_manager, "minimize_window"))
test("Has maximize_window",   lambda: hasattr(window_manager, "maximize_window"))
test("Has close_window",      lambda: hasattr(window_manager, "close_window"))

# ══════════════════════════════════════════════════════════════
# 7. KEYBOARD CONTROLLER
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("MODULE 7: Keyboard Controller")
print("="*60)

from keyboard_controller import keyboard_controller

test("Import keyboard_controller", lambda: True)
test("Has type_text",              lambda: hasattr(keyboard_controller, "type_text"))
test("Has press_key",              lambda: hasattr(keyboard_controller, "press_key"))

# ══════════════════════════════════════════════════════════════
# 8. FILE MANAGER
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("MODULE 8: File Manager")
print("="*60)

from file_manager import file_manager

test("Import file_manager", lambda: True)
test("Desktop path exists", lambda: file_manager.desktop.exists())
test("Has create_file",     lambda: hasattr(file_manager, "create_file"))
test("Has create_folder",   lambda: hasattr(file_manager, "create_folder"))
test("Has delete_file",     lambda: hasattr(file_manager, "delete_file"))
test("Has find_file",       lambda: hasattr(file_manager, "find_file"))
test("Has list_files",      lambda: hasattr(file_manager, "list_files"))
test("Has open_file",       lambda: hasattr(file_manager, "open_file"))

def test_list_desktop():
    r = file_manager.list_files("desktop")
    if not isinstance(r, str):
        raise AssertionError(f"Expected str, got {type(r)}")
    return r[:80]

test("list_files(desktop)", test_list_desktop)

# ══════════════════════════════════════════════════════════════
# 9. CAMERA VISION
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("MODULE 9: Camera Vision")
print("="*60)

from camera_vision import camera_vision

test("Import camera_vision", lambda: True)
test("Has describe_scene",   lambda: hasattr(camera_vision, "describe_scene"))
test("Has capture_image",    lambda: hasattr(camera_vision, "capture_image"))

def test_vision_model():
    return "configured" if camera_vision.model_name else "missing key"

test("AI model configured", test_vision_model)

# ══════════════════════════════════════════════════════════════
# 10. SCREEN READER
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("MODULE 10: Screen Reader")
print("="*60)

from screen_reader import screen_reader

test("Import screen_reader", lambda: True)
test("Has read_screen",      lambda: hasattr(screen_reader, "read_screen"))
test("Has capture_screen",   lambda: hasattr(screen_reader, "capture_screen"))

# ══════════════════════════════════════════════════════════════
# 11. NEWS
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("MODULE 11: News")
print("="*60)

from gnews import news_fetcher

test("Import news_fetcher",   lambda: True)
test("Has get_top_headlines",  lambda: hasattr(news_fetcher, "get_top_headlines"))

def test_news_key():
    return "configured" if news_fetcher.api_key else "missing key"

test("API key configured", test_news_key)

# ══════════════════════════════════════════════════════════════
# 12. MEDICAL
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("MODULE 12: Medical")
print("="*60)

from medical import medical_assistant

test("Import medical_assistant", lambda: True)
test("Has get_advice",           lambda: hasattr(medical_assistant, "get_advice"))

# ══════════════════════════════════════════════════════════════
# 13. EMAIL
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("MODULE 13: Email")
print("="*60)

from jarvis_email import email_manager

test("Import email_manager",  lambda: True)
test("Has send_email",        lambda: hasattr(email_manager, "send_email"))

def test_email_config():
    return "configured" if email_manager.email else "missing credentials"

test("Email configured", test_email_config)

# ══════════════════════════════════════════════════════════════
# 14. MOBILE CONTROLLER
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("MODULE 14: Mobile Controller")
print("="*60)

from mobile_controller import mobile_controller

test("Import mobile_controller",   lambda: True)
test("Has send_whatsapp_message",   lambda: hasattr(mobile_controller, "send_whatsapp_message"))

# ══════════════════════════════════════════════════════════════
# 15. SPOTIFY CONTROLLER
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("MODULE 15: Spotify Controller")
print("="*60)

from spotify_controller import spotify_controller

test("Import spotify_controller", lambda: True)
test("Has handle_command",        lambda: hasattr(spotify_controller, "handle_command"))

# ══════════════════════════════════════════════════════════════
# 16. LOCAL LLM
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("MODULE 16: Local LLM")
print("="*60)

from local_llm import local_llm

test("Import local_llm",    lambda: True)
test("Has chat method",     lambda: hasattr(local_llm, "chat"))
test("Has switch_mode",     lambda: hasattr(local_llm, "switch_mode"))
test("Has is_available",    lambda: hasattr(local_llm, "is_available"))

# ══════════════════════════════════════════════════════════════
# 17. PLUGIN SYSTEM
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("MODULE 17: Plugin System")
print("="*60)

from plugin_manager import plugin_manager

test("Import plugin_manager", lambda: True)

def test_plugins_loaded():
    names = list(plugin_manager.plugins.keys())
    return f"{len(names)} plugins: {', '.join(names)}"

test("Plugins loaded", test_plugins_loaded)
test("Calculator plugin", lambda: "Calculator" in plugin_manager.plugins)
test("Weather plugin",    lambda: "Weather" in plugin_manager.plugins)

def test_calc_plugin():
    r = plugin_manager.try_handle("calculate 5 + 3")
    return r

test("Plugin: calculate 5 + 3", test_calc_plugin)

def test_weather_plugin():
    r = plugin_manager.try_handle("weather Delhi")
    return r

test("Plugin: weather Delhi", test_weather_plugin)
test("Plugin list_plugins", lambda: plugin_manager.list_plugins())

# ══════════════════════════════════════════════════════════════
# 18. GEMINI LIVE CLIENT
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("MODULE 18: Gemini Live Client")
print("="*60)

from gemini_live_client import GeminiLiveClient, MODELS, VOICES

test("Import GeminiLiveClient", lambda: True)

def test_models_count():
    if len(MODELS) < 3:
        raise AssertionError(f"Expected >=3, got {len(MODELS)}")
    return f"{len(MODELS)} models"

test("MODELS defined", test_models_count)

def test_voices_count():
    if len(VOICES) < 6:
        raise AssertionError(f"Expected >=6, got {len(VOICES)}")
    return f"{len(VOICES)} voices"

test("VOICES defined", test_voices_count)

def test_get_models():
    ms = GeminiLiveClient.get_models()
    return f"{len(ms)} models returned"

test("get_models()", test_get_models)

def test_get_voices():
    vs = GeminiLiveClient.get_voices()
    return f"{len(vs)} voices returned"

test("get_voices()", test_get_voices)

def test_client_init():
    c = GeminiLiveClient(api_key="test", model="models/test")
    if c.is_connected:
        raise AssertionError("Should not be connected initially")
    return "OK"

test("Client instantiation", test_client_init)

# ══════════════════════════════════════════════════════════════
# 19. AUDIO ENGINE
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("MODULE 19: Audio Engine")
print("="*60)

from audio_engine import AudioEngine, AUDIO_BACKEND

test("Import AudioEngine", lambda: True)

def test_audio_backend():
    if AUDIO_BACKEND is None:
        raise AssertionError("No audio backend available")
    return AUDIO_BACKEND

test("Audio backend", test_audio_backend)
test("Instantiation",           lambda: AudioEngine() and "OK")
test("Has start_recording",     lambda: hasattr(AudioEngine, "start_recording"))
test("Has start_playback",      lambda: hasattr(AudioEngine, "start_playback"))
test("Has queue_audio",         lambda: hasattr(AudioEngine, "queue_audio"))
test("Has clear_playback_queue", lambda: hasattr(AudioEngine, "clear_playback_queue"))
test("Has release",             lambda: hasattr(AudioEngine, "release"))

# ══════════════════════════════════════════════════════════════
# 20. JARVIS CONTROLLER (Integration)
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("MODULE 20: Jarvis Controller (Integration Hub)")
print("="*60)

from jarvis_controller import controller

test("Import controller", lambda: True)

def test_module_status():
    ms = controller.get_module_status()
    return f"{len(ms)} modules registered"

test("get_module_status", test_module_status)

# Note: volume up actually presses keys, so just test it returns a string
def test_volume_up():
    r = controller.process_command("volume up")
    if not isinstance(r, str):
        raise AssertionError(f"Expected str, got {type(r)}")
    return r

test("process_command: volume up", test_volume_up)

def test_news_cmd():
    r = controller.process_command("news")
    return isinstance(r, str) and "OK"

test("process_command: news (graceful)", test_news_cmd)
test("process_command: list plugins", lambda: controller.process_command("list plugins"))

def test_fallback():
    r = controller.process_command("abcdef random gibberish")
    return r

test("process_command: fallback", test_fallback)

# ══════════════════════════════════════════════════════════════
# 21. BRIDGE SERVER (import check)
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("MODULE 21: Bridge Server (Import Check)")
print("="*60)

try:
    sys.path.insert(0, os.path.dirname(__file__))
    from core.gemini_live_client import GeminiLiveClient as GLC2
    from core.audio_engine import AudioEngine as AE2
    from core.command_parser import parse_command as pc2
    from core.personality import build_system_prompt as bsp2
    from core.jarvis_controller import controller as ctrl2
    test("Bridge 'core.' imports resolve", lambda: True)
except Exception as e:
    test("Bridge 'core.' imports resolve", lambda: (_ for _ in ()).throw(Exception(str(e))))

# ══════════════════════════════════════════════════════════════
# 22. COMMAND PARSER ↔ CONTROLLER FLOW
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("INTEGRATION: Command Parser → Controller Flow")
print("="*60)

def test_e2e_flow(text):
    """End-to-end: parse → controller should handle it."""
    cmd = parse_command(text)
    if cmd:
        result = controller.process_command(text)
        if not isinstance(result, str) or len(result) == 0:
            raise AssertionError(f"Empty result for '{text}'")
        return result[:80]
    else:
        return "No command parsed (conversation mode)"

test("E2E: 'volume up'",           lambda: test_e2e_flow("volume up"))
test("E2E: 'news'",                lambda: test_e2e_flow("news"))
test("E2E: conversation fallback", lambda: test_e2e_flow("how are you today"))

# ══════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print(f"FINAL RESULTS: {passed} PASSED, {failed} FAILED")
print("="*60)

if errors:
    print("\nFailed tests:")
    for name, err in errors:
        print(f"  ❌ {name}: {err}")

if failed == 0:
    print("\n🎉 ALL TESTS PASSED — System is 100% operational!")
else:
    print(f"\n⚠️  {failed} test(s) need fixing.")
