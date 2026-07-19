import os
import re

parser_path = "c:\\Users\\Acer\\Desktop\\alok\\sivi\\backend\\core\\command_parser.py"

with open(parser_path, "r", encoding="utf-8") as f:
    content = f.read()

# We will inject the Trie class after the keywords (around line 163)
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
        
        # Exact prefix match
        for i, char in enumerate(text):
            if char in node:
                node = node[char]
                # A match is valid if it reaches a terminal node AND it's followed by a space or end of string.
                if '__cmd__' in node:
                    if i + 1 == len(text) or text[i+1] == ' ':
                        last_match_cmd = node['__cmd__']
                        last_match_len = i + 1
            else:
                break
                
        return last_match_cmd, last_match_len

    def search_anywhere(self, text: str):
        # Aho-Corasick style O(N) substring search
        best_cmd = None
        best_kw = ""
        best_len = -1
        
        n = len(text)
        for i in range(n):
            node = self.root
            j = i
            last_cmd = None
            last_len = -1
            while j < n and text[j] in node:
                node = node[text[j]]
                if '__cmd__' in node:
                    # Valid if word boundary
                    if (i == 0 or text[i-1] == ' ') and (j + 1 == n or text[j+1] == ' '):
                        last_cmd = node['__cmd__']
                        last_len = j - i + 1
                j += 1
            if last_cmd and last_len > best_len:
                best_cmd = last_cmd
                best_len = last_len
                best_kw = text[i:i+best_len]
        return best_cmd, best_kw

_global_trie = CommandTrie()
_trie_initialized = False

def _init_trie():
    global _trie_initialized
    if _trie_initialized: return
    
    mapping = {
        "OPEN_APP": OPEN_KEYWORDS,
        "CLOSE_APP": CLOSE_KEYWORDS,
        "SWITCH_APP": SWITCH_APP_KEYWORDS,
        "VOLUME_UP": VOLUME_UP_KEYWORDS,
        "VOLUME_DOWN": VOLUME_DOWN_KEYWORDS,
        "MUTE": MUTE_KEYWORDS,
        "SCREENSHOT": SCREENSHOT_KEYWORDS,
        "READ_SCREEN": SCREEN_READ_KEYWORDS,
        "LOCK_SCREEN": LOCK_KEYWORDS,
        "SHUTDOWN": SHUTDOWN_KEYWORDS,
        "RESTART": RESTART_KEYWORDS,
        "SLEEP": SLEEP_KEYWORDS,
        "BRIGHTNESS_UP": BRIGHTNESS_UP_KEYWORDS,
        "BRIGHTNESS_DOWN": BRIGHTNESS_DOWN_KEYWORDS,
        "PLAY_YOUTUBE": PLAY_KEYWORDS,
        "SEARCH": SEARCH_KEYWORDS,
        "TYPE_TEXT": TYPE_KEYWORDS,
        "CREATE_FILE": FILE_CREATE_KEYWORDS,
        "DELETE_FILE": FILE_DELETE_KEYWORDS,
        "CREATE_FOLDER": FOLDER_CREATE_KEYWORDS,
        "DELETE_FOLDER": FOLDER_DELETE_KEYWORDS,
        "FIND_FILE": FIND_FILE_KEYWORDS,
        "LIST_FILES": LIST_FILES_KEYWORDS,
        "OPEN_FILE": OPEN_FILE_KEYWORDS,
        "LIST_WINDOWS": LIST_WINDOWS_KEYWORDS,
        "READ_CLIPBOARD": READ_CLIPBOARD_KEYWORDS,
        "WRITE_CLIPBOARD": WRITE_CLIPBOARD_KEYWORDS,
        "MEDIA_PLAY_PAUSE": MEDIA_PLAY_PAUSE_KEYWORDS,
        "MEDIA_NEXT": MEDIA_NEXT_KEYWORDS,
        "MEDIA_PREV": MEDIA_PREV_KEYWORDS,
        "SYSTEM_STATUS": SYSTEM_STATUS_KEYWORDS,
        "GET_WEATHER": WEATHER_KEYWORDS,
        "REMEMBER": REMEMBER_KEYWORDS,
        "FORGET_ALL": FORGET_KEYWORDS,
        "ANALYZE_EMOTION": EMOTION_ANALYSIS_KEYWORDS,
        "ANALYZE_WELLNESS": WELLNESS_KEYWORDS,
        "DESCRIBE_SCENE": DESCRIBE_SCENE_KEYWORDS,
        "SEND_EMAIL": EMAIL_KEYWORDS,
        "SEND_WHATSAPP": WHATSAPP_KEYWORDS,
        "WHATSAPP_READ": WHATSAPP_READ_KEYWORDS,
        "DEV_RUN_CMD": DEV_CMD_KEYWORDS,
        "DEV_EXECUTE_SCRIPT": DEV_EXECUTE_SCRIPT_KEYWORDS,
        "DEV_SPAWN_SUBAGENT": DEV_SPAWN_SUBAGENT_KEYWORDS,
        "DEV_GIT_STATUS": DEV_GIT_STATUS_KEYWORDS,
        "SWARM_RUN": SWARM_KEYWORDS,
        "SWITCH_MODE": SWITCH_MODE_KEYWORDS,
        "REFRESH_DASHBOARD": DASHBOARD_REFRESH_KEYWORDS,
        "MOBILE_HANDOFF": MOBILE_HANDOFF_KEYWORDS,
        "SET_TIMER": TIMER_KEYWORDS,
        "SCHEDULE_TASK": SCHEDULE_TASK_KEYWORDS,
        "CALENDAR_EVENTS": CALENDAR_KEYWORDS,
        "UIA_CLICK": UIA_CLICK_KEYWORDS,
        "UIA_TYPE": UIA_TYPE_KEYWORDS,
        "UIA_READ": UIA_READ_KEYWORDS,
        "BROWSER_READ_PAGE": BROWSER_READ_PAGE_KEYWORDS,
        "BROWSER_FULLSCREEN": BROWSER_FULLSCREEN_KEYWORDS,
        "BROWSER_STATUS": BROWSER_STATUS_KEYWORDS,
        "BROWSER_SCROLL": BROWSER_SCROLL_KEYWORDS,
        "TAB_NEXT": TAB_NEXT_KEYWORDS,
        "TAB_PREV": TAB_PREV_KEYWORDS,
        "TAB_NEW": TAB_NEW_KEYWORDS,
        "TAB_CLOSE": TAB_CLOSE_KEYWORDS,
        "VOLUME_SET": VOLUME_SET_KEYWORDS
    }
    
    for cmd_type, kw_list in mapping.items():
        for kw in kw_list:
            _global_trie.insert(kw.lower(), cmd_type)
            
    _trie_initialized = True
"""

# Replace the _exact_phrase section with our new Trie logic
content = re.sub(r'# ── Cached compiled patterns ──.*?(?=def parse_command)', trie_code, content, flags=re.DOTALL)

# Now, we rewrite the parse_command signature to call _init_trie
init_hook = """
def parse_command(text: str) -> "PCCommand | None":
    _init_trie()
"""
content = content.replace('def parse_command(text: str) -> "PCCommand | None":', init_hook)

# We will inject an early O(1) Trie lookup right after the 'Normalise' block (around line 250)
trie_lookup = """
    # ── Advanced O(1) Trie Routing ────────────────────────────────
    cmd_type, match_len = _global_trie.search_longest_prefix(text_lower)
    kw = text_lower[:match_len] if match_len > 0 else ""
    
    if not cmd_type:
        cmd_type, kw = _global_trie.search_anywhere(text_lower)
"""

content = re.sub(r'(text_lower = text_lower\.strip\(\)\n)', r'\1' + trie_lookup, content)

with open(parser_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Injected Trie architecture into command_parser.py")
