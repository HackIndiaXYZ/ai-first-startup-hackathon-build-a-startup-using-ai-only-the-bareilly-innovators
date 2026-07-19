import re

with open("c:\\Users\\Acer\\Desktop\\alok\\sivi\\backend\\core\\command_parser.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Inject Trie definition
trie_code = """
class CommandTrie:
    def __init__(self):
        self.root = {}
    
    def insert(self, phrase: str, cmd_type: str):
        node = self.root
        for char in phrase:
            if char not in node:
                node[char] = {}
            node = node[char]
        node['__cmd__'] = cmd_type
        
    def search_longest_prefix(self, text: str):
        node = self.root
        last_match_cmd = None
        last_match_len = -1
        for i, char in enumerate(text):
            if char in node:
                node = node[char]
                if '__cmd__' in node:
                    if i + 1 == len(text) or text[i+1] == ' ':
                        last_match_cmd = node['__cmd__']
                        last_match_len = i + 1
            else:
                break
        return last_match_cmd, last_match_len

    def search_anywhere(self, text: str):
        best_cmd, best_kw, best_len = None, "", -1
        n = len(text)
        for i in range(n):
            node = self.root
            j = i
            last_cmd, last_len = None, -1
            while j < n and text[j] in node:
                node = node[text[j]]
                if '__cmd__' in node:
                    if (i == 0 or text[i-1] == ' ') and (j + 1 == n or text[j+1] == ' '):
                        last_cmd = node['__cmd__']
                        last_len = j - i + 1
                j += 1
            if last_cmd and last_len > best_len:
                best_cmd, best_len, best_kw = last_cmd, last_len, text[i:i+best_len]
        return best_cmd, best_kw

_global_trie = CommandTrie()
_trie_initialized = False

def _init_trie():
    global _trie_initialized
    if _trie_initialized: return
    mapping = {
        "OPEN_APP": OPEN_KEYWORDS, "CLOSE_APP": CLOSE_KEYWORDS, "SWITCH_APP": SWITCH_APP_KEYWORDS,
        "VOLUME_UP": VOLUME_UP_KEYWORDS, "VOLUME_DOWN": VOLUME_DOWN_KEYWORDS, "MUTE": MUTE_KEYWORDS,
        "SCREENSHOT": SCREENSHOT_KEYWORDS, "READ_SCREEN": SCREEN_READ_KEYWORDS, "LOCK_SCREEN": LOCK_KEYWORDS,
        "SHUTDOWN": SHUTDOWN_KEYWORDS, "RESTART": RESTART_KEYWORDS, "SLEEP": SLEEP_KEYWORDS,
        "BRIGHTNESS_UP": BRIGHTNESS_UP_KEYWORDS, "BRIGHTNESS_DOWN": BRIGHTNESS_DOWN_KEYWORDS,
        "PLAY_YOUTUBE": PLAY_KEYWORDS, "SEARCH": SEARCH_KEYWORDS, "TYPE_TEXT": TYPE_KEYWORDS,
        "CREATE_FILE": FILE_CREATE_KEYWORDS, "DELETE_FILE": FILE_DELETE_KEYWORDS,
        "CREATE_FOLDER": FOLDER_CREATE_KEYWORDS, "DELETE_FOLDER": FOLDER_DELETE_KEYWORDS,
        "FIND_FILE": FIND_FILE_KEYWORDS, "LIST_FILES": LIST_FILES_KEYWORDS, "OPEN_FILE": OPEN_FILE_KEYWORDS,
        "LIST_WINDOWS": LIST_WINDOWS_KEYWORDS, "READ_CLIPBOARD": READ_CLIPBOARD_KEYWORDS,
        "WRITE_CLIPBOARD": WRITE_CLIPBOARD_KEYWORDS, "MEDIA_PLAY_PAUSE": MEDIA_PLAY_PAUSE_KEYWORDS,
        "MEDIA_NEXT": MEDIA_NEXT_KEYWORDS, "MEDIA_PREV": MEDIA_PREV_KEYWORDS,
        "SYSTEM_STATUS": SYSTEM_STATUS_KEYWORDS, "GET_WEATHER": WEATHER_KEYWORDS,
        "REMEMBER": REMEMBER_KEYWORDS, "FORGET_ALL": FORGET_KEYWORDS,
        "ANALYZE_EMOTION": EMOTION_ANALYSIS_KEYWORDS, "ANALYZE_WELLNESS": WELLNESS_KEYWORDS,
        "DESCRIBE_SCENE": DESCRIBE_SCENE_KEYWORDS, "SEND_EMAIL": EMAIL_KEYWORDS,
        "SEND_WHATSAPP": WHATSAPP_KEYWORDS, "WHATSAPP_READ": WHATSAPP_READ_KEYWORDS,
        "DEV_RUN_CMD": DEV_CMD_KEYWORDS, "DEV_EXECUTE_SCRIPT": DEV_EXECUTE_SCRIPT_KEYWORDS,
        "DEV_SPAWN_SUBAGENT": DEV_SPAWN_SUBAGENT_KEYWORDS, "DEV_GIT_STATUS": DEV_GIT_STATUS_KEYWORDS,
        "SWARM_RUN": SWARM_KEYWORDS, "SWITCH_MODE": SWITCH_MODE_KEYWORDS,
        "REFRESH_DASHBOARD": DASHBOARD_REFRESH_KEYWORDS, "MOBILE_HANDOFF": MOBILE_HANDOFF_KEYWORDS,
        "SET_TIMER": TIMER_KEYWORDS, "SCHEDULE_TASK": SCHEDULE_TASK_KEYWORDS,
        "CALENDAR_EVENTS": CALENDAR_KEYWORDS, "UIA_CLICK": UIA_CLICK_KEYWORDS,
        "UIA_TYPE": UIA_TYPE_KEYWORDS, "UIA_READ": UIA_READ_KEYWORDS,
        "BROWSER_READ_PAGE": BROWSER_READ_PAGE_KEYWORDS, "BROWSER_FULLSCREEN": BROWSER_FULLSCREEN_KEYWORDS,
        "BROWSER_STATUS": BROWSER_STATUS_KEYWORDS, "BROWSER_SCROLL": BROWSER_SCROLL_KEYWORDS,
        "TAB_NEXT": TAB_NEXT_KEYWORDS, "TAB_PREV": TAB_PREV_KEYWORDS, "TAB_NEW": TAB_NEW_KEYWORDS,
        "TAB_CLOSE": TAB_CLOSE_KEYWORDS, "VOLUME_SET": VOLUME_SET_KEYWORDS
    }
    for cmd_type, kw_list in mapping.items():
        for kw in kw_list:
            _global_trie.insert(kw.lower(), cmd_type)
    _trie_initialized = True
"""

content = re.sub(r'# ── Cached compiled patterns ──.*?(?=def parse_command)', trie_code, content, flags=re.DOTALL)
content = content.replace('def parse_command(text: str) -> "PCCommand | None":', 'def parse_command(text: str) -> "PCCommand | None":\n    _init_trie()')

trie_lookup = """
    # ── Advanced O(1) Trie Routing ────────────────────────────────
    cmd_type, match_len = _global_trie.search_longest_prefix(text_lower)
    matched_kw = text_lower[:match_len] if match_len > 0 else ""
    
    if not cmd_type:
        cmd_type, matched_kw = _global_trie.search_anywhere(text_lower)
        
    if not cmd_type:
        return None  # No command found by Trie!
"""
content = re.sub(r'(text_lower = text_lower\.strip\(\)\n)', r'\1' + trie_lookup, content)

# 2. Refactor loops to use cmd_type
replacements = [
    # Prefix matches
    (r'for kw in OPEN_KEYWORDS:\s*\n\s*if text_lower\.startswith\(kw \+ " "\):', r'if cmd_type == "OPEN_APP":\n            kw = matched_kw'),
    (r'for kw in CLOSE_KEYWORDS:\s*\n\s*if text_lower\.startswith\(kw \+ " "\) or text_lower == kw:', r'if cmd_type == "CLOSE_APP":\n        kw = matched_kw'),
    (r'for kw in SWITCH_APP_KEYWORDS:\s*\n\s*if text_lower\.startswith\(kw \+ " "\):', r'if cmd_type == "SWITCH_APP":\n        kw = matched_kw'),
    (r'for kw in PLAY_KEYWORDS:\s*\n\s*if text_lower\.startswith\(kw \+ " "\):', r'if cmd_type == "PLAY_YOUTUBE":\n        kw = matched_kw'),
    (r'for kw in SEARCH_KEYWORDS:\s*\n\s*if text_lower\.startswith\(kw \+ " "\):', r'if cmd_type == "SEARCH":\n        kw = matched_kw'),
    (r'for kw in TYPE_KEYWORDS:\s*\n\s*if text_lower\.startswith\(kw \+ " "\):', r'if cmd_type == "TYPE_TEXT":\n        kw = matched_kw'),
    (r'for kw in DASHBOARD_REFRESH_KEYWORDS:\s*\n\s*if text_lower\.startswith\(kw\):', r'if cmd_type == "REFRESH_DASHBOARD":\n        kw = matched_kw'),
    (r'for kw in LIST_FILES_KEYWORDS:\s*\n\s*if text_lower\.startswith\(kw\):', r'if cmd_type == "LIST_FILES":\n        kw = matched_kw'),
    (r'for kw in EMAIL_KEYWORDS:\s*\n\s*if text_lower\.startswith\(kw \+ " "\):', r'if cmd_type == "SEND_EMAIL":\n        kw = matched_kw'),
    (r'for kw in WHATSAPP_KEYWORDS:\s*\n\s*if text_lower\.startswith\(kw \+ " "\) or text_lower == kw:', r'if cmd_type == "SEND_WHATSAPP":\n        kw = matched_kw'),
    (r'for kw in WHATSAPP_READ_KEYWORDS:\s*\n\s*if text_lower\.startswith\(kw\):', r'if cmd_type == "WHATSAPP_READ":\n        kw = matched_kw'),
    (r'for kw in DEV_CMD_KEYWORDS:\s*\n\s*if text_lower\.startswith\(kw \+ " "\):', r'if cmd_type == "DEV_RUN_CMD":\n        kw = matched_kw'),
    (r'for kw in DEV_EXECUTE_SCRIPT_KEYWORDS:\s*\n\s*if text_lower\.startswith\(kw \+ " "\):', r'if cmd_type == "DEV_EXECUTE_SCRIPT":\n        kw = matched_kw'),
    (r'for kw in DEV_SPAWN_SUBAGENT_KEYWORDS:\s*\n\s*if text_lower\.startswith\(kw \+ " "\):', r'if cmd_type == "DEV_SPAWN_SUBAGENT":\n        kw = matched_kw'),
    (r'for kw in SWARM_KEYWORDS:\s*\n\s*if text_lower\.startswith\(kw \+ " "\):', r'if cmd_type == "SWARM_RUN":\n        kw = matched_kw'),
    (r'for kw in SWITCH_MODE_KEYWORDS:\s*\n\s*if text_lower\.startswith\(kw \+ " "\):', r'if cmd_type == "SWITCH_MODE":\n        kw = matched_kw'),
    (r'for kw in MOBILE_HANDOFF_KEYWORDS:\s*\n\s*if text_lower\.startswith\(kw \+ " "\):', r'if cmd_type == "MOBILE_HANDOFF":\n        kw = matched_kw'),
    (r'for kw in SCHEDULE_TASK_KEYWORDS:\s*\n\s*if text_lower\.startswith\(kw\):', r'if cmd_type == "SCHEDULE_TASK":\n        kw = matched_kw'),
    (r'for kw in UIA_CLICK_KEYWORDS:\s*\n\s*if text_lower\.startswith\(kw \+ " "\):', r'if cmd_type == "UIA_CLICK":\n        kw = matched_kw'),
    (r'for kw in UIA_TYPE_KEYWORDS:\s*\n\s*if text_lower\.startswith\(kw \+ " "\):', r'if cmd_type == "UIA_TYPE":\n        kw = matched_kw'),
    
    # Anywhere matches
    (r'for kw in FILE_CREATE_KEYWORDS:\s*\n\s*if kw in text_lower:', r'if cmd_type == "CREATE_FILE":\n        kw = matched_kw'),
    (r'for kw in FILE_DELETE_KEYWORDS:\s*\n\s*if kw in text_lower:', r'if cmd_type == "DELETE_FILE":\n        kw = matched_kw'),
    (r'for kw in FOLDER_CREATE_KEYWORDS:\s*\n\s*if kw in text_lower:', r'if cmd_type == "CREATE_FOLDER":\n        kw = matched_kw'),
    (r'for kw in FOLDER_DELETE_KEYWORDS:\s*\n\s*if kw in text_lower:', r'if cmd_type == "DELETE_FOLDER":\n        kw = matched_kw'),
    (r'for kw in FIND_FILE_KEYWORDS:\s*\n\s*if kw in text_lower:', r'if cmd_type == "FIND_FILE":\n        kw = matched_kw'),
    (r'for kw in OPEN_FILE_KEYWORDS:\s*\n\s*if kw in text_lower:', r'if cmd_type == "OPEN_FILE":\n        kw = matched_kw'),
    (r'for kw in BROWSER_SCROLL_KEYWORDS:\s*\n\s*if kw in text_lower:', r'if cmd_type == "BROWSER_SCROLL":\n        kw = matched_kw'),
    (r'for kw in WEATHER_KEYWORDS:\s*\n\s*if kw in text_lower:', r'if cmd_type == "GET_WEATHER":\n        kw = matched_kw'),
    (r'for kw in REMEMBER_KEYWORDS:\s*\n\s*if kw in text_lower:', r'if cmd_type == "REMEMBER":\n        kw = matched_kw'),
]

for pat, repl in replacements:
    content = re.sub(pat, repl, content)

with open("c:\\Users\\Acer\\Desktop\\alok\\sivi\\backend\\core\\command_parser.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Parser refactored successfully.")
