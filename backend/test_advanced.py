"""Final verification suite for all advanced improvements."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("SIVI ADVANCED SYSTEMS VERIFICATION")
print("=" * 60)

# ── Test 1: command_parser.py ─────────────────────────────────────────────────
print("\n[1] Command Parser Tests")
from core.command_parser import parse_command

tests = [
    # Basic commands
    ("open chrome",                      "OPEN_APP",       "chrome"),
    ("close",                            None,             None),
    ("close chrome",                     "CLOSE_APP",      "chrome"),
    # Timer via Trie
    ("set timer for 5 minutes",          "SET_TIMER",      None),
    ("timer lagao 10 minute",            "SET_TIMER",      None),
    # File
    ("find file report.pdf",             "FIND_FILE",      "report.pdf"),
    ("delete file named file.txt",       "DELETE_FILE",    None),
    # Volume
    ("volume up",                        "VOLUME_UP",      None),
    # Fuzzy match
    ("open chrom",                       "OPEN_APP",       "chrome"),
    # WhatsApp multi-word contact
    ("send message to Rao Alok Yadav saying hello", "SEND_WHATSAPP", None),
    # Wake word before command
    ("hey sivi open chrome",             "OPEN_APP",       "chrome"),
    ("sivi volume up",                   "VOLUME_UP",      None),
    # Anywhere match
    ("hey close chrome",                 "CLOSE_APP",      "chrome"),
    # Ambiguity: bare 'play' -> media play/pause
    ("play",                             "MEDIA_PLAY_PAUSE", None),
    ("play music",                       "MEDIA_PLAY_PAUSE", None),
    # Play with query -> YouTube
    ("play despacito",                   "PLAY_YOUTUBE",   None),
    # Search
    ("search for python tutorials",      "SEARCH",         None),
]

passed = failed = 0
for text, exp_type, exp_app in tests:
    r = parse_command(text)
    got_type = r.type if r else None
    ok = (got_type == exp_type)
    if ok and exp_app and r:
        # Also check app_name param if specified
        got_app = r.params.get("app_name") or r.params.get("name") or r.params.get("query", "")
        ok = (exp_app in got_app)
    
    status = "PASS" if ok else "FAIL"
    if ok: passed += 1
    else:  failed += 1
    print(f"  {status} | '{text}' -> {exp_type} | got={got_type}")

print(f"\n  Parser: {passed} passed, {failed} failed / {len(tests)} total")

# ── Test 2: hindi_voice.py ────────────────────────────────────────────────────
print("\n[2] Hindi Voice Tests (word-boundary + expanded dict)")
from core.hindi_voice import hindi_voice

hindi_tests = [
    ("file dhundo report.pdf",      "find file"),
    ("awaaz badhao",                "volume up"),
    ("band karo chrome",            "close chrome"),
    ("screenshot le lo",            "take screenshot"),
    ("computer band karo",          "shutdown the computer"),
    ("timer lagao 5 minute",        "set timer for 5 minute"),
    ("message bhejo rahul ko hello","send message rahul ko hello"),
    # Word boundary: "hello" should NOT trigger "lo" -> "take photo"
    ("hello sivi",                  "hello sivi"),
    # Phonetic normalization
    ("watsapp kholo",               "whatsapp open"),
]

h_passed = h_failed = 0
for text, expected_contains in hindi_tests:
    result = hindi_voice.try_translate(text)
    ok = expected_contains.lower() in result.lower()
    status = "PASS" if ok else "FAIL"
    if ok: h_passed += 1
    else:  h_failed += 1
    print(f"  {status} | '{text}' -> '{result}' | expected to contain '{expected_contains}'")

print(f"\n  Hindi Voice: {h_passed} passed, {h_failed} failed / {len(hindi_tests)} total")

# ── Test 3: file_manager.py ───────────────────────────────────────────────────
print("\n[3] File Manager Tests")
from core.file_manager import file_manager

# Check class structure
ok = hasattr(file_manager, 'db_path')
print(f"  {'PASS' if ok else 'FAIL'} | FileManager has db_path (SQLite enabled)")

ok = hasattr(file_manager, '_indexer_worker')
print(f"  {'PASS' if ok else 'FAIL'} | FileManager has background indexer")

ok = hasattr(file_manager, '_extract_ext_filter')
print(f"  {'PASS' if ok else 'FAIL'} | FileManager has extension-aware search")

ok = hasattr(file_manager, '_index_add') and hasattr(file_manager, '_index_remove')
print(f"  {'PASS' if ok else 'FAIL'} | FileManager has live index update methods")

# Test extension extraction
exts = file_manager._extract_ext_filter("find my excel file budget")
ok = ".xlsx" in exts
print(f"  {'PASS' if ok else 'FAIL'} | Extension hint: 'excel' -> {exts}")

exts = file_manager._extract_ext_filter("find pdf report")
ok = ".pdf" in exts
print(f"  {'PASS' if ok else 'FAIL'} | Extension hint: 'pdf' -> {exts}")

# Test query cleaning
q = file_manager._clean_query("find my pdf file named report")
ok = "report" in q and "pdf" not in q and "file" not in q
print(f"  {'PASS' if ok else 'FAIL'} | Query clean: 'find my pdf file named report' -> '{q}'")

# Wait a bit for indexer to start
time.sleep(0.5)
sz = file_manager.index_size
print(f"  INFO | Index size after 0.5s: {sz} files (may still be building)")

# ── Test 4: notification_monitor.py ──────────────────────────────────────────
print("\n[4] Notification Monitor Tests")
from core.notification_monitor import NotificationMonitor, HIGH_PRIORITY_APPS

mon = NotificationMonitor()
ok = mon._should_speak("WhatsApp")
print(f"  {'PASS' if ok else 'FAIL'} | WhatsApp is high-priority")
ok = mon._should_speak("Telegram")
print(f"  {'PASS' if ok else 'FAIL'} | Telegram is high-priority")
ok = not mon._should_speak("Windows Update")
print(f"  {'PASS' if ok else 'FAIL'} | Windows Update is NOT high-priority (suppressed)")
ok = mon._debounce_window("WhatsApp") == 2.0
print(f"  {'PASS' if ok else 'FAIL'} | WhatsApp debounce = 2s")
ok = mon._debounce_window("Windows Update") == 30.0
print(f"  {'PASS' if ok else 'FAIL'} | Windows Update debounce = 30s")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
total_pass = passed + h_passed
total_fail = failed + h_failed
print(f"FINAL: {total_pass} passed, {total_fail} failed")
print("=" * 60)
