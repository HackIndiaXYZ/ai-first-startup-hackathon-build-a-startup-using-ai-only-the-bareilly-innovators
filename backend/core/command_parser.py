"""
SIVI -- Voice Command Parser (PC Edition)
Parses transcribed speech (Hinglish + English) into structured PC commands.
Returns None if no command matches so Gemini handles it as conversation.
"""

import re
import string
import difflib
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class PCCommand:
    type: str
    params: dict = field(default_factory=dict)
    requires_confirmation: bool = False


# ── App Name Mappings ─────────────────────────────────────────────

APP_ALIASES = {
    "chrome": "chrome", "google chrome": "chrome", "browser": "chrome",
    "firefox": "firefox", "mozilla": "firefox",
    "edge": "edge", "microsoft edge": "edge",
    "brave": "brave",
    "whatsapp": "whatsapp", "telegram": "telegram", "discord": "discord",
    "zoom": "zoom", "teams": "teams", "microsoft teams": "teams",
    "meet": "meet", "google meet": "meet", "skype": "skype", "slack": "slack",
    "youtube": "youtube", "instagram": "instagram", "facebook": "facebook",
    "twitter": "twitter", "x": "twitter", "linkedin": "linkedin", "reddit": "reddit",
    "spotify": "spotify", "vlc": "vlc", "media player": "media player",
    "netflix": "netflix", "prime video": "prime video",
    "notepad": "notepad", "word": "word", "microsoft word": "word",
    "excel": "excel", "powerpoint": "powerpoint", "ppt": "powerpoint",
    "vs code": "vscode", "visual studio code": "vscode", "code": "vscode",
    "sublime": "sublime", "terminal": "terminal", "cmd": "cmd",
    "powershell": "powershell",
    "settings": "settings", "control panel": "control panel",
    "task manager": "task manager", "calculator": "calculator",
    "calendar": "calendar", "clock": "clock",
    "file explorer": "explorer", "explorer": "explorer",
    "paint": "paint", "snipping tool": "snipping tool",
    "steam": "steam", "epic games": "epic games",
    "paytm": "paytm", "phonepe": "phonepe", "gpay": "gpay",
    "amazon": "amazon", "flipkart": "flipkart", "swiggy": "swiggy", "zomato": "zomato",
}

OPEN_KEYWORDS = ["open", "launch", "start", "run", "kholo", "khol do", "chalu karo", "shuru karo"]
CLOSE_KEYWORDS = ["close", "quit", "exit", "band karo", "band kar do", "hatao"]
SWITCH_APP_KEYWORDS = ["switch to", "go to", "switch app to", "open window"]
VOLUME_UP_KEYWORDS = ["volume up", "volume badhao", "volume badha do", "awaz badhao",
                      "awaaz badhao", "louder", "increase volume", "sound badhao"]
VOLUME_DOWN_KEYWORDS = ["volume down", "volume kam karo", "awaz kam karo",
                        "quieter", "decrease volume", "sound kam karo"]
MUTE_KEYWORDS = ["mute the volume", "mute karo", "awaz band karo", "awaaz band karo", "silent mode"]
SCREENSHOT_KEYWORDS = ["take a screenshot", "take screenshot", "screenshot le lo",
                       "screen capture", "capture the screen", "ss le lo", "screenshot lelo"]
SCREEN_READ_KEYWORDS = ["read my screen", "screen padho", "what's on screen",
                        "summarize screen", "screen batao", "what's on my screen", "what is on screen"]
LOCK_KEYWORDS = ["lock the screen", "lock screen", "screen lock", "lock karo", "lock kar do"]
SHUTDOWN_KEYWORDS = ["shutdown the computer", "shut down the computer", "band karo computer",
                     "computer band karo", "pc band karo", "turn off computer", "turn off the pc"]
RESTART_KEYWORDS = ["restart the computer", "reboot the computer", "restart karo",
                    "reboot karo", "computer restart karo"]
SLEEP_KEYWORDS = ["sleep mode", "put to sleep", "so jao computer",
                  "sleep karo computer", "computer ko sleep karo",
                  "ok bye", "goodbye", "see you later", "alvida", "phir milenge", "good night sivi"]
# NOTE: bare 'bye', 'tata' removed -- too short and cause false positives in long sentences
BRIGHTNESS_UP_KEYWORDS = ["brightness up", "brightness badhao", "make it brighter",
                           "screen bright karo", "roshan karo", "increase brightness"]
BRIGHTNESS_DOWN_KEYWORDS = ["brightness down", "brightness kam karo", "make it dimmer",
                             "screen dim karo", "andhera karo", "decrease brightness"]
PLAY_KEYWORDS = ["play", "chalao", "bajao", "suno"]
SEARCH_KEYWORDS = ["search for", "search", "google", "search karo", "dhundho"]
TYPE_KEYWORDS = ["type", "likho", "likh do"]
FILE_CREATE_KEYWORDS = ["create file", "file banao", "naya file"]
FILE_DELETE_KEYWORDS = ["delete file", "file delete karo", "file hatao"]
FOLDER_CREATE_KEYWORDS = ["create folder", "folder banao", "naya folder"]
FOLDER_DELETE_KEYWORDS = ["delete folder", "folder delete karo", "folder hatao"]
FIND_FILE_KEYWORDS = ["find file", "file dhundho", "file khojo"]
LIST_FILES_KEYWORDS = ["list files in", "list files"]
OPEN_FILE_KEYWORDS = ["open file", "file kholo", "open the file"]
LIST_WINDOWS_KEYWORDS = ["what apps are open", "what windows are open", "read browsers",
                         "read active apps", "show open apps", "check open apps"]
READ_CLIPBOARD_KEYWORDS = ["read clipboard", "what's on clipboard", "clipboard batao", "clipboard kya hai"]
WRITE_CLIPBOARD_KEYWORDS = ["copy this to clipboard", "clipboard mein copy karo"]
MEDIA_PLAY_PAUSE_KEYWORDS = ["play media", "pause media", "play music", "pause music",
                             "stop music", "resume music", "play video", "pause video"]
MEDIA_NEXT_KEYWORDS = ["next track", "next song", "next video", "skip song", "agle gaana"]
MEDIA_PREV_KEYWORDS = ["previous track", "previous song", "previous video", "last song", "pichla gaana"]
SYSTEM_STATUS_KEYWORDS = ["system status", "pc health", "check system", "system kaisa hai",
                          "what time is it", "current time", "what is the date", "aaj ki date",
                          "time kya ho raha hai", "time kya hai", "battery status", "check battery"]
WEATHER_KEYWORDS = ["get weather", "weather in", "weather of", "climate in", "mausam kaisa hai", "weather"]
REMEMBER_KEYWORDS = ["remember", "yaad rakho", "memorize"]
FORGET_KEYWORDS = ["forget all", "forget everything", "clear memory", "yaad bhool jao", "memory clear karo"]
EMOTION_ANALYSIS_KEYWORDS = ["how do i look", "read my face", "check my mood",
                             "mera mood kaisa hai", "analyze my emotion", "meri shakal dekho",
                             "mujhe dekho", "mood batao", "main kaisa dikh raha hoon"]
WELLNESS_KEYWORDS = ["wellness check", "posture check", "eye strain", "health check",
                     "sehat kaisi hai", "aankhein thak gayi", "kamar dard", "posture dekho"]
DESCRIBE_SCENE_KEYWORDS = ["take photo", "what do you see", "photo khicho", "describe what you see"]
SWITCH_MODE_KEYWORDS = ["switch mode to", "change mode to", "switch personality to",
                        "switch to", "mode badlo", "personality badlo"]
MINIMIZE_KEYWORDS = ["minimize", "chota karo"]
MAXIMIZE_KEYWORDS = ["maximize", "bada karo"]
SNAP_LEFT_KEYWORDS = ["snap to left", "snap left", "snap window to left", "window left mein karo"]
SNAP_RIGHT_KEYWORDS = ["snap to right", "snap right", "snap window to right", "window right mein karo"]
CALENDAR_KEYWORDS = ["calendar", "schedule", "my events", "today's events", "what's scheduled"]
MEDICAL_KEYWORDS = ["health", "medical", "headache", "fever", "bukhar", "sir dard",
                    "pet dard", "khansi", "thakan", "cough", "stomach"]
EMAIL_KEYWORDS = ["send email"]
WHATSAPP_KEYWORDS = ["send message", "send msg", "whatsapp message", "whatsapp karo",
                     "message bhejo", "message bhej do", "whatsapp pe bhej",
                     "send whatsapp message", "send a message", "send a whatsapp"]
WHATSAPP_READ_KEYWORDS = ["read whatsapp", "whatsapp check", "read messages from",
                          "read latest messages", "read unread msg", "read unread messages",
                          "naya message padho", "unread message", "read message",
                          "check messages from", "messages padho", "whatsapp messages"]
WHATSAPP_CALL_KEYWORDS = ["voice call", "video call", "call on whatsapp",
                          "whatsapp call", "whatsapp pe call"]
WHATSAPP_MEDIA_KEYWORDS = ["send document", "send file", "photo bhej", "send attachment",
                           "file bhej", "document bhej"]
WHATSAPP_VOICE_NOTE_KEYWORDS = ["send voice note", "voice note", "audio message",
                                "voice message bhej"]
PRESS_KEYWORDS = ["press"]
MOUSE_CLICK_KEYWORDS = ["mouse click", "left click", "right click", "double click"]
MOUSE_SCROLL_KEYWORDS = ["scroll up", "scroll down"]
MOUSE_MOVE_KEYWORDS = ["move mouse up", "move mouse down", "move mouse left", "move mouse right"]
DEV_CMD_KEYWORDS = ["run command", "execute terminal", "run terminal", "terminal mein chalao"]
DEV_GIT_STATUS_KEYWORDS = ["git status", "check git", "check repository"]
DEV_GIT_COMMIT_KEYWORDS = ["git commit and push", "auto commit", "commit changes"]
DEV_RUN_TESTS_KEYWORDS = ["run tests", "execute tests", "run test suite"]
DEV_KILL_PORT_KEYWORDS = ["kill port", "stop port", "port band karo"]
DEV_ANALYZE_CODE_KEYWORDS = ["analyze code in", "check bugs in", "find bugs in", "code analyze karo"]
DEV_GENERATE_CODE_KEYWORDS = ["write code for", "generate code for", "code likho"]
DEV_EXECUTE_SCRIPT_KEYWORDS = ["execute script to", "write script to", "create script to"]
DEV_SPAWN_SUBAGENT_KEYWORDS = ["spawn subagent to", "spawn agent to", "monitor in background"]
DEV_OPEN_EDITOR_KEYWORDS = ["open in editor", "open in vs code", "open in vscode"]
DEV_CLOSE_EDITOR_KEYWORDS = ["close current file", "close editor tab", "band karo tab"]

DEV_MONITOR_LOGS_KEYWORDS = ["monitor logs in", "watch logs in", "tail logs for", "crash detective for"]
DEV_DB_QUERY_KEYWORDS = ["query database", "run sql", "check database"]
SWARM_KEYWORDS = ["delegate to swarm", "assign background task", "research in background", "background research"]
GRAPH_ADD_KEYWORDS = ["graph add", "learn relation"]
GRAPH_QUERY_KEYWORDS = ["graph query", "what do you know about"]
MOBILE_HANDOFF_KEYWORDS = ["send to phone", "message my phone", "alert me on phone", "push to phone"]
TIMER_KEYWORDS = ["set timer for", "set alarm for", "timer lagao", "alarm lagao", "remind me in"]
SCHEDULE_TASK_KEYWORDS = ["schedule task to", "schedule command to", "run this later", "schedule event to"]
LIST_SCHEDULED_KEYWORDS = ["what is scheduled", "list scheduled tasks", "list my alarms"]
VOLUME_SET_KEYWORDS = ["set volume to", "volume set karo", "volume ko"]
SHOW_RESEARCH_KEYWORDS = ["show_research:"]
TAB_NEXT_KEYWORDS = ["next tab", "agle tab", "go to next tab"]
TAB_PREV_KEYWORDS = ["previous tab", "pichle tab", "go to previous tab"]
TAB_NEW_KEYWORDS = ["new tab", "open tab", "naya tab"]
TAB_CLOSE_KEYWORDS = ["close tab", "tab band karo"]
BROWSER_READ_PAGE_KEYWORDS = ["read this page", "read page", "read website", "website padho", "summarize page"]
BROWSER_FULLSCREEN_KEYWORDS = ["browser full screen", "toggle full screen", "full screen karo", "video full screen", "full screen mode"]
BROWSER_SCROLL_KEYWORDS = ["scroll page down", "scroll page up", "scroll to top", "scroll to bottom"]
BROWSER_STATUS_KEYWORDS = ["browser status", "get open tabs", "list tabs", "open tabs", "how many tabs", "check open tabs"]
UIA_CLICK_KEYWORDS = ["uia click", "native click"]
UIA_TYPE_KEYWORDS = ["uia type", "native type"]
UIA_READ_KEYWORDS = ["uia read", "native read", "read app tree"]

# ── New Phase 1 Commands ──────────────────────────────────────────────
PROCESS_KILL_KEYWORDS = ["kill process", "end process", "force close", "band karo process", "stop task"]
PROCESS_LIST_KEYWORDS = ["list processes", "running tasks", "kya chal raha hai process", "cpu usage"]
DISK_INFO_KEYWORDS = ["disk info", "storage info", "kitna space hai", "hard drive status", "free space"]
IP_ADDRESS_KEYWORDS = ["my ip", "ip address", "mera ip kya hai", "network ip"]
PING_KEYWORDS = ["ping", "check latency"]
AUDIO_DEVICE_KEYWORDS = ["switch audio", "audio device", "change speaker", "speaker badlo"]
DISPLAY_SETTINGS_KEYWORDS = ["display settings", "screen resolution"]
SCREEN_RECORD_KEYWORDS = ["record screen", "start recording", "screen record karo"]
EMPTY_RECYCLE_KEYWORDS = ["empty recycle bin", "clear bin", "kachra saaf karo", "empty trash"]
NETWORK_STATUS_KEYWORDS = ["network status", "internet speed", "wifi status", "internet chal raha hai"]
INSTALLED_APPS_KEYWORDS = ["installed apps", "list apps", "programs list"]
STARTUP_MANAGE_KEYWORDS = ["startup apps", "manage startup"]
CLIPBOARD_HISTORY_KEYWORDS = ["clipboard history", "copy history"]
HOTSPOT_TOGGLE_KEYWORDS = ["hotspot on", "hotspot off", "toggle hotspot", "hotspot chalao"]
NIGHT_LIGHT_KEYWORDS = ["night light", "eye care mode", "blue light filter"]
DO_NOT_DISTURB_KEYWORDS = ["do not disturb", "dnd", "focus mode", "disturb mat karo"]
TASK_SCHEDULER_KEYWORDS = ["task scheduler", "scheduled tasks"]
SERVICE_CONTROL_KEYWORDS = ["restart service", "stop service", "start service"]
POWER_PLAN_KEYWORDS = ["power plan", "battery saver", "performance mode"]
SYSTEM_UPTIME_KEYWORDS = ["uptime", "system uptime", "kitni der se chal raha hai", "how long is pc on"]

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
                best_cmd, best_len, best_kw = last_cmd, last_len, text[i:i+last_len]
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
         "MOBILE_HANDOFF": MOBILE_HANDOFF_KEYWORDS,
        "SET_TIMER": TIMER_KEYWORDS, "SCHEDULE_TASK": SCHEDULE_TASK_KEYWORDS,
        "CALENDAR_EVENTS": CALENDAR_KEYWORDS, "UIA_CLICK": UIA_CLICK_KEYWORDS,
        "UIA_TYPE": UIA_TYPE_KEYWORDS, "UIA_READ": UIA_READ_KEYWORDS,
        "BROWSER_READ_PAGE": BROWSER_READ_PAGE_KEYWORDS, "BROWSER_FULLSCREEN": BROWSER_FULLSCREEN_KEYWORDS,
        "BROWSER_STATUS": BROWSER_STATUS_KEYWORDS, "BROWSER_SCROLL": BROWSER_SCROLL_KEYWORDS,
        "TAB_NEXT": TAB_NEXT_KEYWORDS, "TAB_PREV": TAB_PREV_KEYWORDS, "TAB_NEW": TAB_NEW_KEYWORDS,
        "TAB_CLOSE": TAB_CLOSE_KEYWORDS, "VOLUME_SET": VOLUME_SET_KEYWORDS,
        "SHOW_RESEARCH": SHOW_RESEARCH_KEYWORDS,
        "PROCESS_KILL": PROCESS_KILL_KEYWORDS, "PROCESS_LIST": PROCESS_LIST_KEYWORDS,
        "DISK_INFO": DISK_INFO_KEYWORDS, "IP_ADDRESS": IP_ADDRESS_KEYWORDS,
        "PING": PING_KEYWORDS, "AUDIO_DEVICE": AUDIO_DEVICE_KEYWORDS,
        "DISPLAY_SETTINGS": DISPLAY_SETTINGS_KEYWORDS, "SCREEN_RECORD": SCREEN_RECORD_KEYWORDS,
        "EMPTY_RECYCLE": EMPTY_RECYCLE_KEYWORDS, "NETWORK_STATUS": NETWORK_STATUS_KEYWORDS,
        "INSTALLED_APPS": INSTALLED_APPS_KEYWORDS, "STARTUP_MANAGE": STARTUP_MANAGE_KEYWORDS,
        "CLIPBOARD_HISTORY": CLIPBOARD_HISTORY_KEYWORDS, "HOTSPOT_TOGGLE": HOTSPOT_TOGGLE_KEYWORDS,
        "NIGHT_LIGHT": NIGHT_LIGHT_KEYWORDS, "DO_NOT_DISTURB": DO_NOT_DISTURB_KEYWORDS,
        "TASK_SCHEDULER": TASK_SCHEDULER_KEYWORDS, "SERVICE_CONTROL": SERVICE_CONTROL_KEYWORDS,
        "POWER_PLAN": POWER_PLAN_KEYWORDS, "SYSTEM_UPTIME": SYSTEM_UPTIME_KEYWORDS
    }
    for cmd_type, kw_list in mapping.items():
        for kw in kw_list:
            _global_trie.insert(kw.lower(), cmd_type)
    _trie_initialized = True
def parse_command(text: str) -> "PCCommand | None":
    _init_trie()
    if not text or not text.strip():
        return None

    # Fast-path: exact technical tag types (no params)
    text_upper = text.strip().upper()
    VALID_NO_PARAM_TYPES = {
        "SHUTDOWN", "RESTART", "SLEEP", "VOLUME_UP", "VOLUME_DOWN", "MUTE",
        "BRIGHTNESS_UP", "BRIGHTNESS_DOWN", "SCREENSHOT", "READ_SCREEN", "LOCK_SCREEN",
        "WIFI_ON", "WIFI_OFF", "BLUETOOTH_ON", "BLUETOOTH_OFF", "MEDIA_PLAY_PAUSE",
        "MEDIA_NEXT", "MEDIA_PREV", "READ_CLIPBOARD", "NEWS", "SYSTEM_STATUS",
        "READ_WINDOWS", "FORGET_ALL", "ANALYZE_EMOTION", "DESCRIBE_SCENE", "DEV_GIT_STATUS",
        "TAB_NEXT", "TAB_PREV", "TAB_NEW", "TAB_CLOSE", "BROWSER_READ_PAGE", "BROWSER_FULLSCREEN",
        "BROWSER_STATUS", "REFRESH_DASHBOARD", "CALENDAR_EVENTS", "ANALYZE_WELLNESS",
        "PROCESS_LIST", "DISK_INFO", "IP_ADDRESS", "EMPTY_RECYCLE", "NETWORK_STATUS",
        "SYSTEM_UPTIME", "INSTALLED_APPS", "STARTUP_MANAGE", "CLIPBOARD_HISTORY",
        "HOTSPOT_TOGGLE", "NIGHT_LIGHT", "DO_NOT_DISTURB", "TASK_SCHEDULER"
    }
    if text_upper in VALID_NO_PARAM_TYPES:
        return PCCommand(type=text_upper)

    # Fast-path 2: technical tag types with parameters (e.g. "OPEN_APP chrome")
    parts = text.strip().split(" ", 1)
    if len(parts) == 2:
        cmd_type = parts[0].upper().rstrip(":")
        cmd_val = parts[1].strip()
        
        # Strip trailing punctuation for the value if needed
        while cmd_val and cmd_val[-1] in string.punctuation:
            cmd_val = cmd_val[:-1]
            
        if cmd_type == "OPEN_APP":
            resolved = APP_ALIASES.get(cmd_val.lower(), cmd_val.lower())
            return PCCommand(type="OPEN_APP", params={"app_name": resolved, "raw": cmd_val})
        elif cmd_type == "CLOSE_APP":
            return PCCommand(type="CLOSE_APP", params={"app_name": cmd_val.lower()})
        elif cmd_type == "SWITCH_APP":
            return PCCommand(type="SWITCH_APP", params={"app_name": cmd_val.lower()})
        elif cmd_type == "TYPE_TEXT":
            return PCCommand(type="TYPE_TEXT", params={"text": cmd_val})
        elif cmd_type == "SEARCH":
            return PCCommand(type="SEARCH", params={"query": cmd_val})
        elif cmd_type == "PRESS_KEY":
            return PCCommand(type="PRESS_KEY", params={"key": cmd_val})
        elif cmd_type in ["PLAY_YOUTUBE", "PLAY_SPOTIFY"]:
            return PCCommand(type=cmd_type, params={"query": cmd_val})
        elif cmd_type == "DEV_RUN_CMD":
            return PCCommand(type="DEV_RUN_CMD", params={"command": cmd_val})
        elif cmd_type == "GET_WEATHER":
            return PCCommand(type="GET_WEATHER", params={"location": cmd_val})
        elif cmd_type == "REMEMBER":
            return PCCommand(type="REMEMBER", params={"fact": cmd_val})
        elif cmd_type == "SWARM_RUN":
            return PCCommand(type="SWARM_RUN", params={"query": cmd_val})
        elif cmd_type in ["CREATE_FILE", "DELETE_FILE", "OPEN_FILE", "FIND_FILE"]:
            return PCCommand(type=cmd_type, params={"name": cmd_val})
        elif cmd_type == "LIST_FILES":
            return PCCommand(type="LIST_FILES", params={"folder": cmd_val})
        elif cmd_type in ["MINIMIZE_WINDOW", "MAXIMIZE_WINDOW"]:
            return PCCommand(type=cmd_type, params={"app_name": cmd_val})
        elif cmd_type == "SWITCH_MODE":
            return PCCommand(type="SWITCH_MODE", params={"mode": cmd_val})
        elif cmd_type == "SET_TIMER":
            # Extract number from SET_TIMER <amount> <unit>
            try:
                sec_match = re.search(r'\d+', cmd_val)
                amount = int(sec_match.group(0)) if sec_match else 60
                unit_val = cmd_val.lower()
                multiplier = 3600 if "hour" in unit_val or "hr" in unit_val else (60 if "min" in unit_val else 1)
                return PCCommand(type="SET_TIMER", params={"seconds": amount * multiplier, "label": "Timer"})
            except:
                pass
        elif cmd_type == "SHOW_RESEARCH":
             return PCCommand(type="SHOW_RESEARCH", params={"topic": cmd_val})
        elif cmd_type == "PROCESS_KILL":
             return PCCommand(type="PROCESS_KILL", params={"process_name": cmd_val})
        elif cmd_type == "PING":
             return PCCommand(type="PING", params={"host": cmd_val})
        elif cmd_type == "AUDIO_DEVICE":
             return PCCommand(type="AUDIO_DEVICE", params={"device_name": cmd_val})
        elif cmd_type in ["DISPLAY_SETTINGS", "SCREEN_RECORD", "SERVICE_CONTROL"]:
             return PCCommand(type=cmd_type, params={"action": cmd_val})
        elif cmd_type == "POWER_PLAN":
             return PCCommand(type="POWER_PLAN", params={"plan": cmd_val})

    # Normalise
    text_lower = text.lower().strip().replace('"', '').replace("'", "")
    while text_lower and text_lower[-1] in string.punctuation:
        text_lower = text_lower[:-1]
    text_lower = text_lower.strip()

    # ── Strip Wake Words BEFORE Trie routing ──────────────────────
    # Must come before Trie so the Trie doesn't see "sivi" as part of input
    _wake_words = ["hey sivi", "hey jarvis", "sivi", "jarvis"]
    for _ww in _wake_words:
        if text_lower.startswith(_ww + " "):
            text_lower = text_lower[len(_ww):].strip()
            break
        elif text_lower == _ww:
            return None  # Bare wake word with no command

    # ── Advanced O(1) Trie Routing ────────────────────────────────
    cmd_type, match_len = _global_trie.search_longest_prefix(text_lower)
    matched_kw = text_lower[:match_len] if match_len > 0 else ""
    
    if not cmd_type:
        cmd_type, matched_kw = _global_trie.search_anywhere(text_lower)
        
        
    if not cmd_type:
        return None

    if cmd_type in VALID_NO_PARAM_TYPES:
        return PCCommand(type=cmd_type)



    # ── WiFi / Bluetooth (MUST be before generic open/close) ──────
    if re.search(r'\bwifi\b|\bwi-fi\b|\bwireless\b|\binternet\b', text_lower):
        if re.search(r'\bon\b|\bchalu\b|\bturn on\b|\benable\b|\bconnect\b', text_lower):
            return PCCommand(type="WIFI_ON")
        elif re.search(r'\boff\b|\bband\b|\bturn off\b|\bdisable\b|\bdisconnect\b', text_lower):
            return PCCommand(type="WIFI_OFF")

    if re.search(r'\bbluetooth\b|\bbt\b', text_lower):
        if re.search(r'\bon\b|\bchalu\b|\bturn on\b|\benable\b', text_lower):
            return PCCommand(type="BLUETOOTH_ON")
        elif re.search(r'\boff\b|\bband\b|\bturn off\b|\bdisable\b', text_lower):
            return PCCommand(type="BLUETOOTH_OFF")

    # ── Volume set to specific level ──────────────────────────────
    vol_match = re.search(r'(?:set volume to|volume set karo|volume ko)\s+(\d+)', text_lower)
    if vol_match:
        level = int(vol_match.group(1))
        return PCCommand(type="VOLUME_SET", params={"level": max(0, min(100, level))})

    # ── Timer / Alarm ─────────────────────────────────────────────
    if cmd_type == "SET_TIMER":
        kw = matched_kw
        rest = text_lower.split(kw, 1)[-1].strip()
        t_match = re.search(r'(\d+)\s*(second|minute|hour|sec|min|hr)', rest)
        if t_match:
            amount = int(t_match.group(1))
            unit = t_match.group(2)
            seconds = amount * (3600 if unit.startswith("h") else 60 if unit.startswith("m") else 1)
            label = rest.split(t_match.group(0))[-1].strip() or "Timer"
            return PCCommand(type="SET_TIMER", params={"seconds": seconds, "label": label})

    # ── Open App (MUST be before Open File to avoid "open file explorer" collision) ──
    # Skip if the text matches a developer command (e.g. "run command git status")
    _dev_prefixes = DEV_CMD_KEYWORDS + DEV_EXECUTE_SCRIPT_KEYWORDS + DEV_SPAWN_SUBAGENT_KEYWORDS
    _is_dev_cmd = any(text_lower.startswith(dp) for dp in _dev_prefixes)
    if not _is_dev_cmd:
        if cmd_type == "OPEN_APP":
            kw = matched_kw
            app_name = text_lower.split(kw, 1)[-1].strip()
            if app_name:
                # Check if it's an explicit file open request like "open file X"
                if app_name.startswith("file ") and app_name != "file explorer":
                    pass  # Handled by longest prefix match
                resolved = APP_ALIASES.get(app_name)
                # Fuzzy match: if exact alias not found, try close matches (typo tolerance)
                if not resolved:
                    close_matches = difflib.get_close_matches(app_name, APP_ALIASES.keys(), n=1, cutoff=0.75)
                    if close_matches:
                        resolved = APP_ALIASES[close_matches[0]]
                    else:
                        resolved = app_name
                return PCCommand(type="OPEN_APP", params={"app_name": resolved, "raw": app_name})

    # ── Open File ─────────────────────────────────────────────────
    if cmd_type == "OPEN_FILE":
        kw = matched_kw
        name = text_lower.replace(kw, "").strip()
        if name:
            return PCCommand(type="OPEN_FILE", params={"name": name})

    # ── Shutdown / Restart / Sleep ────────────────────────────────
    if cmd_type == "SHUTDOWN":
        return PCCommand(type="SHUTDOWN")
    if cmd_type == "RESTART":
        return PCCommand(type="RESTART")
    if cmd_type == "SLEEP":
        return PCCommand(type="SLEEP")

    # ── Tab Control ───────────────────────────────────────────────
    if cmd_type == "TAB_NEXT": return PCCommand(type="TAB_NEXT")
    if cmd_type == "TAB_PREV": return PCCommand(type="TAB_PREV")
    if cmd_type == "TAB_NEW":  return PCCommand(type="TAB_NEW")
    if cmd_type == "TAB_CLOSE":return PCCommand(type="TAB_CLOSE")

    # ── Advanced Browser Control ──────────────────────────────────
    if cmd_type == "BROWSER_READ_PAGE": return PCCommand(type="BROWSER_READ_PAGE")
    if cmd_type == "BROWSER_FULLSCREEN": return PCCommand(type="BROWSER_FULLSCREEN")
    if cmd_type == "BROWSER_STATUS": return PCCommand(type="BROWSER_STATUS")
    
    if cmd_type == "BROWSER_SCROLL":
        kw = matched_kw
        if "up" in text_lower: d = "up"
        elif "top" in text_lower: d = "top"
        elif "bottom" in text_lower: d = "bottom"
        else: d = "down"
        return PCCommand(type="BROWSER_SCROLL", params={"direction": d})

    # ── Close App ─────────────────────────────────────────────────
    if cmd_type == "CLOSE_APP":
        kw = matched_kw
        app_name = text_lower.split(kw, 1)[-1].strip()
        # Guard: bare "close" with no app name should not close random foreground window
        if not app_name:
            return None
        if app_name != "tab":
            return PCCommand(type="CLOSE_APP", params={"app_name": app_name})

    # ── Switch App ────────────────────────────────────────────────
    if cmd_type == "SWITCH_APP":
        kw = matched_kw
        app_name = text_lower.split(kw, 1)[-1].strip()
        # Avoid collision: 'switch to professional/gf/dev' goes to personality; 'go to next/prev tab' goes to tab
        if app_name and app_name not in ["professional", "assistant", "gf", "developer"] \
                and "tab" not in app_name:
            return PCCommand(type="SWITCH_APP", params={"app_name": app_name})
    # ── Volume ────────────────────────────────────────────────────
    if cmd_type in ["VOLUME_UP", "VOLUME_DOWN", "MUTE"]:
        return PCCommand(type=cmd_type)

    # ── Brightness ────────────────────────────────────────────────
    if cmd_type in ["BRIGHTNESS_UP", "BRIGHTNESS_DOWN"]:
        return PCCommand(type=cmd_type)

    # ── Screenshot ────────────────────────────────────────────────
    if cmd_type == "SCREENSHOT":
        return PCCommand(type="SCREENSHOT")

    # ── Screen Reader ─────────────────────────────────────────────
    if cmd_type == "READ_SCREEN":
        return PCCommand(type="READ_SCREEN")

    # ── Lock Screen ───────────────────────────────────────────────
    if cmd_type == "LOCK_SCREEN":
        return PCCommand(type="LOCK_SCREEN")

    # ── Media Controls ────────────────────────────────────────────
    if cmd_type in ["MEDIA_PLAY_PAUSE", "MEDIA_NEXT", "MEDIA_PREV"]:
        return PCCommand(type=cmd_type)

    # ── Power Controls ────────────────────────────────────────────
    if cmd_type in ["SLEEP", "SHUTDOWN", "RESTART"]:
        return PCCommand(type=cmd_type, requires_confirmation=(cmd_type != "SLEEP"))
    # ── Play on YouTube / Spotify ─────────────────────────────────
    if cmd_type == "PLAY_YOUTUBE":
        kw = matched_kw
        query = text_lower.split(kw, 1)[-1].strip()
        if query:
            if "spotify" in text_lower:
                return PCCommand(type="PLAY_SPOTIFY", params={"query": query.replace("on spotify", "").strip()})
            return PCCommand(type="PLAY_YOUTUBE", params={"query": query})
        else:
            # No query after 'play'/'chalao' -- user means play/pause media
            return PCCommand(type="MEDIA_PLAY_PAUSE")

    # ── Google Search ─────────────────────────────────────────────
    if cmd_type == "SEARCH":
        kw = matched_kw
        query = text_lower.split(kw, 1)[-1].strip()
        if query:
            return PCCommand(type="SEARCH", params={"query": query})

    # ── Type Text ─────────────────────────────────────────────────
    if cmd_type == "TYPE_TEXT":
        kw = matched_kw
        content = text.strip().split(kw, 1)[-1].strip().strip(' "\'')
        if content:
            return PCCommand(type="TYPE_TEXT", params={"text": content})

    # ── Keyboard Press ────────────────────────────────────────────
    for kw in PRESS_KEYWORDS:
        if text_lower.startswith(kw + " "):
            key = text_lower.split(kw, 1)[-1].strip()
            return PCCommand(type="PRESS_KEY", params={"key": key})

    # ── Mouse Control ─────────────────────────────────────────────
    for kw in MOUSE_CLICK_KEYWORDS:
        if kw in text_lower:
            button = "right" if "right" in text_lower else "left"
            double = "double" in text_lower
            return PCCommand(type="MOUSE_CLICK", params={"button": button, "double": double})

    for kw in MOUSE_SCROLL_KEYWORDS:
        if kw in text_lower:
            direction = "up" if "up" in text_lower else "down"
            return PCCommand(type="MOUSE_SCROLL", params={"direction": direction})

    for kw in MOUSE_MOVE_KEYWORDS:
        if kw in text_lower:
            direction = kw.replace("move mouse ", "").strip()
            amt_match = re.search(r'\b(\d+)\b', text_lower)
            amount = int(amt_match.group(1)) if amt_match else 200
            return PCCommand(type="MOUSE_MOVE", params={"direction": direction, "amount": amount})

    if "move mouse to" in text_lower:
        coords = re.findall(r'\b(\d+)\b', text_lower)
        if len(coords) >= 2:
            return PCCommand(type="MOUSE_MOVE_TO", params={"x": int(coords[0]), "y": int(coords[1])})

    # ── Window Snap ───────────────────────────────────────────────

    # ── File Operations ───────────────────────────────────────────
    if cmd_type == "CREATE_FILE":
        kw = matched_kw
        name = text_lower.split(kw, 1)[-1].strip()
        if name:
            return PCCommand(type="CREATE_FILE", params={"name": name})

    if cmd_type == "DELETE_FILE":
        kw = matched_kw
        name = text_lower.split(kw, 1)[-1].strip()
        if name:
            return PCCommand(type="DELETE_FILE", params={"name": name})

    if cmd_type == "CREATE_FOLDER":
        kw = matched_kw
        name = text_lower.split(kw, 1)[-1].strip()
        if name:
            return PCCommand(type="CREATE_FOLDER", params={"name": name})

    if cmd_type == "DELETE_FOLDER":
        kw = matched_kw
        name = text_lower.split(kw, 1)[-1].strip()
        if name:
            return PCCommand(type="DELETE_FOLDER", params={"name": name})

    if cmd_type == "FIND_FILE":
        kw = matched_kw
        name = text_lower.split(kw, 1)[-1].strip()
        if name:
            return PCCommand(type="FIND_FILE", params={"name": name})

    if cmd_type == "LIST_FILES":
        kw = matched_kw
        folder = text_lower.split(kw, 1)[-1].strip()
        return PCCommand(type="LIST_FILES", params={"folder": folder})

    for kw in LIST_WINDOWS_KEYWORDS:
        if kw in text_lower:
            return PCCommand(type="READ_WINDOWS")

    for kw in READ_CLIPBOARD_KEYWORDS:
        if kw in text_lower:
            return PCCommand(type="READ_CLIPBOARD")

    for kw in WRITE_CLIPBOARD_KEYWORDS:
        if text_lower.startswith(kw):
            content = text.strip().split(kw, 1)[-1].strip()
            return PCCommand(type="WRITE_CLIPBOARD", params={"text": content})

    # ── News ──────────────────────────────────────────────────────
    if re.search(r'\bnews\b|\bheadlines\b|\bkhabar\b|\bsamachar\b', text_lower):
        return PCCommand(type="NEWS")

    # ── System Monitor / Weather ────────────────────────────────────────────

    if cmd_type == "GET_WEATHER":
        kw = matched_kw
        # Extract location
        loc = text_lower.split(kw, 1)[-1].strip()
        if not loc:
            loc = "" # Let wttr.in auto-detect via IP
        return PCCommand(type="GET_WEATHER", params={"location": loc})

    # ── Memory Vault ──────────────────────────────────────────────
    if cmd_type == "REMEMBER":
        kw = matched_kw
        fact = text_lower.replace(kw, "").strip()
        if fact:
            return PCCommand(type="REMEMBER", params={"fact": fact})

    for kw in FORGET_KEYWORDS:
        if kw in text_lower:
            return PCCommand(type="FORGET_ALL")

    # ── Camera Vision ─────────────────────────────────────────────
    for kw in EMOTION_ANALYSIS_KEYWORDS:
        if kw in text_lower:
            return PCCommand(type="ANALYZE_EMOTION")

    for kw in DESCRIBE_SCENE_KEYWORDS:
        if kw in text_lower:
            return PCCommand(type="DESCRIBE_SCENE")

    # ── Personality Switch ────────────────────────────────────────
    for kw in SWITCH_MODE_KEYWORDS:
        if kw in text_lower:
            mode = text_lower.replace(kw, "").strip()
            if "professional" in mode or "pro" in mode:
                mode = "professional"
            elif "assistant" in mode or "sathi" in mode:
                mode = "assistant"
            elif "developer" in mode or "dev" in mode or "coder" in mode:
                mode = "developer"
            elif "gf" in mode or "girlfriend" in mode or "romantic" in mode or "love" in mode:
                mode = "gf"
            else:
                mode = "gf"
            return PCCommand(type="SWITCH_MODE", params={"mode": mode})

    # ── Window Management ─────────────────────────────────────────
    for kw in MINIMIZE_KEYWORDS:
        if text_lower.startswith(kw):
            win_name = text_lower.replace(kw, "").strip() or None
            return PCCommand(type="MINIMIZE_WINDOW", params={"app_name": win_name})
    for kw in MAXIMIZE_KEYWORDS:
        if text_lower.startswith(kw):
            win_name = text_lower.replace(kw, "").strip() or None
            return PCCommand(type="MAXIMIZE_WINDOW", params={"app_name": win_name})

    # ── Calendar ──────────────────────────────────────────────────
    # Priority: CREATE intent first (before list), to avoid 'schedule X' routing to CALENDAR_EVENTS
    _create_intent = re.search(r'\b(create|add|schedule|set|book)\b', text_lower)
    _has_cal_keyword = any(kw in text_lower for kw in CALENDAR_KEYWORDS)
    
    if _create_intent and _has_cal_keyword:
        # Try to extract the event title from natural language
        for prefix in ["schedule event ", "create event ", "add event ", "book event ",
                       "schedule ", "add to calendar ", "set a reminder "]:
            if prefix in text_lower:
                title = text_lower.split(prefix, 1)[-1].strip()
                if title:
                    return PCCommand(type="CREATE_EVENT", params={"title": title})
        # Fallback: send whole text as quickAdd NLP
        return PCCommand(type="CREATE_EVENT", params={"title": text_lower})

    if _has_cal_keyword:
        return PCCommand(type="CALENDAR_EVENTS")

    # ── Medical ───────────────────────────────────────────────────
    for kw in MEDICAL_KEYWORDS:
        if kw in text_lower:
            return PCCommand(type="MEDICAL_ADVICE", params={"query": text_lower})

    # ── Email ─────────────────────────────────────────────────────
    for kw in EMAIL_KEYWORDS:
        if text_lower.startswith(kw + " ") or text_lower == kw:
            rest = text_lower.split(kw, 1)[-1].strip()
            if rest.startswith("to "): rest = rest[3:].strip()
            to = rest
            content = ""
            for sep in [" saying ", " ki ", " that ", " message ", " ko ", " bol do ", " likh do "]:
                if sep in rest:
                    parts = rest.split(sep, 1)
                    to = parts[0].strip()
                    content = parts[1].strip()
                    break
            if not content and " " in rest:
                parts = rest.split(" ", 1)
                to = parts[0].strip()
                content = parts[1].strip()
            return PCCommand(type="SEND_EMAIL", params={"to": to, "content": content})

    # ── WhatsApp ──────────────────────────────────────────────────
    if cmd_type == "SEND_WHATSAPP":
        kw = matched_kw
        rest = text_lower.split(kw, 1)[-1].strip()
        if rest.startswith("to "):
            rest = rest[3:].strip()
            
        number = rest
        content = ""
        # Priority order: explicit message separators first, then Hindi postpositions
        for sep in [" saying ", " that ", " ki ", " bolke ", " bata ", " bol do ", " likh do ", " message "]:
            if sep in rest:
                parts = rest.split(sep, 1)
                number = parts[0].strip()
                content = parts[1].strip()
                break
            
        # Secondary: try ' ko ' as Hindi separator ("Rahul ko hello" -> name=Rahul, msg=hello)
        if not content and " ko " in rest:
            parts = rest.split(" ko ", 1)
            number = parts[0].strip()
            content = parts[1].strip()

        # Fallback: Only split on bare space if remainder looks like a phone number (all digits)
        # This prevents multi-word names like "Rao Alok Yadav" from being split incorrectly
        if not content and " " in rest:
            first_word = rest.split(" ", 1)[0].strip()
            # If first word is all digits, it's a phone number -- split is safe
            if first_word.replace("+", "").replace("-", "").isdigit():
                number = first_word
                content = rest.split(" ", 1)[1].strip()
            else:
                # Multi-word contact name -- keep entire rest as contact, no content
                number = rest
                content = ""

        # Strip trailing Hindi postposition 'ko' from contact name
        # e.g. "mom ko" -> "mom", "rahul ko" -> "rahul"
        if number.endswith(" ko"):
            number = number[:-3].strip()
                
        return PCCommand(type="SEND_WHATSAPP", params={"number": number, "content": content})

    for kw in WHATSAPP_READ_KEYWORDS:
        if kw in text_lower:
            # Extract contact name: "read messages from Rahul" -> contact="Rahul"
            contact = ""
            for prefix in ["read messages from ", "check messages from ", "read whatsapp from "]:
                if prefix in text_lower:
                    contact = text_lower.split(prefix, 1)[-1].strip()
                    break
            return PCCommand(type="WHATSAPP_READ_CHAT", params={"contact": contact})

    for kw in WHATSAPP_CALL_KEYWORDS:
        if kw in text_lower:
            rest = text_lower.replace(kw, "").strip()
            if rest.startswith("to "): rest = rest[3:].strip()
            if rest.endswith(" on whatsapp"): rest = rest.replace(" on whatsapp", "").strip()
            call_type = "Video call" if "video" in text_lower else "Voice call"
            return PCCommand(type="WHATSAPP_CALL", params={"number": rest, "call_type": call_type})

    for kw in WHATSAPP_MEDIA_KEYWORDS:
        if kw in text_lower:
            rest = text_lower.replace(kw, "").strip()
            number = ""
            filepath = ""
            if " to " in rest:
                parts = rest.split(" to ", 1)
                filepath = parts[0].strip()
                number = parts[1].strip()
            else:
                # fallback
                number = rest
            return PCCommand(type="WHATSAPP_SEND_MEDIA", params={"number": number, "filepath": filepath})

    for kw in WHATSAPP_VOICE_NOTE_KEYWORDS:
        if kw in text_lower:
            rest = text_lower.replace(kw, "").strip()
            if rest.startswith("to "): rest = rest[3:].strip()
            return PCCommand(type="WHATSAPP_VOICE_NOTE", params={"number": rest})

    # ── Developer Commands ────────────────────────────────────────
    for kw in DEV_CMD_KEYWORDS:
        if kw in text_lower:
            cmd_str = text_lower.replace(kw, "").strip()
            if cmd_str:
                return PCCommand(type="DEV_RUN_CMD", params={"command": cmd_str})

    for kw in DEV_GIT_STATUS_KEYWORDS:
        if kw in text_lower:
            return PCCommand(type="DEV_GIT_STATUS")

    for kw in DEV_GIT_COMMIT_KEYWORDS:
        if text_lower.startswith(kw):
            msg = text_lower.replace(kw, "").strip()
            # Default commit message if none provided via voice
            if not msg: msg = "Auto-commit by Sivi"
            return PCCommand(type="DEV_GIT_COMMIT", params={"message": msg})

    for kw in DEV_RUN_TESTS_KEYWORDS:
        if text_lower.startswith(kw):
            cmd = text_lower.replace(kw, "").strip()
            if not cmd: cmd = "pytest" # Default to pytest if not specified
            return PCCommand(type="DEV_RUN_TESTS", params={"cmd": cmd})

    for kw in DEV_KILL_PORT_KEYWORDS:
        if kw in text_lower:
            port = text_lower.replace(kw, "").strip()
            return PCCommand(type="DEV_KILL_PORT", params={"port": port})

    for kw in DEV_ANALYZE_CODE_KEYWORDS:
        if kw in text_lower:
            filename = text_lower.replace(kw, "").strip()
            if filename:
                return PCCommand(type="DEV_ANALYZE_CODE", params={"filename": filename})

    for kw in DEV_GENERATE_CODE_KEYWORDS:
        if text_lower.startswith(kw):
            parts = text_lower.replace(kw, "").split(" in ")
            instructions = parts[0].strip()
            filename = parts[1].strip() if len(parts) > 1 else "output.txt"
            return PCCommand(type="DEV_GENERATE_CODE", params={"filename": filename, "instructions": instructions})

    for kw in DEV_EXECUTE_SCRIPT_KEYWORDS:
        if text_lower.startswith(kw):
            goal = text_lower.replace(kw, "").strip()
            return PCCommand(type="DEV_EXECUTE_SCRIPT", params={"goal": goal})

    for kw in DEV_SPAWN_SUBAGENT_KEYWORDS:
        if text_lower.startswith(kw):
            goal = text_lower.replace(kw, "").strip()
            return PCCommand(type="DEV_SPAWN_SUBAGENT", params={"goal": goal})

    for kw in DEV_OPEN_EDITOR_KEYWORDS:
        if kw in text_lower:
            filename = text_lower.replace(kw, "").strip()
            return PCCommand(type="DEV_OPEN_EDITOR", params={"filename": filename})

    for kw in DEV_CLOSE_EDITOR_KEYWORDS:
        if kw in text_lower:
            return PCCommand(type="DEV_CLOSE_EDITOR")

    for kw in DEV_PATCH_CODE_KEYWORDS:
        if text_lower.startswith(kw):
            parts = text_lower.replace(kw, "").split(" to ")
            if len(parts) >= 2:
                filename = parts[0].strip()
                instructions = parts[1].strip()
                return PCCommand(type="DEV_PATCH_CODE", params={"filename": filename, "instructions": instructions})

    for kw in DEV_AUTO_FIX_KEYWORDS:
        if text_lower.startswith(kw):
            script_path = text_lower.replace(kw, "").strip()
            return PCCommand(type="DEV_AUTO_FIX", params={"script_path": script_path})

    for kw in DEV_MONITOR_LOGS_KEYWORDS:
        if kw in text_lower:
            filename = text_lower.replace(kw, "").strip()
            return PCCommand(type="DEV_MONITOR_LOGS", params={"filename": filename})

    for kw in SHOW_RESEARCH_KEYWORDS:
        if text_lower.startswith(kw):
            topic = text_lower.replace(kw, "", 1).strip()
            return PCCommand(type="SHOW_RESEARCH", params={"topic": topic})

    for kw in DEV_DB_QUERY_KEYWORDS:
        if kw in text_lower:
            # Expected syntax: "query database sqlite:///data.db SELECT * FROM users"
            rest = text_lower.replace(kw, "").strip()
            parts = rest.split(" ", 1)
            conn_str = parts[0].strip()
            query = parts[1].strip() if len(parts) > 1 else ""
            return PCCommand(type="DEV_DB_QUERY", params={"connection_string": conn_str, "query": query})

    for kw in GRAPH_ADD_KEYWORDS:
        if kw in text_lower:
            rest = text_lower.replace(kw, "").strip()
            # Expected syntax: "graph add Alok | likes | Python"
            parts = [p.strip() for p in rest.split("|")]
            if len(parts) == 3:
                return PCCommand(type="GRAPH_ADD", params={"subject": parts[0], "predicate": parts[1], "object": parts[2]})
            
    for kw in GRAPH_QUERY_KEYWORDS:
        if kw in text_lower:
            entity = text_lower.replace(kw, "").strip()
            return PCCommand(type="GRAPH_QUERY", params={"entity": entity})

    for kw in SWARM_KEYWORDS:
        if kw in text_lower:
            query = text_lower.replace(kw, "").strip()
            return PCCommand(type="SWARM_RUN", params={"query": query})

    for kw in MOBILE_HANDOFF_KEYWORDS:
        if text_lower.startswith(kw):
            msg = text_lower.replace(kw, "").strip()
            return PCCommand(type="MOBILE_HANDOFF", params={"message": msg})

    # NOTE: Timer keywords already handled at line 280 (SET_TIMER). This block is for SCHEDULE_TASK only.
    if cmd_type == "SCHEDULE_TASK":
        kw = matched_kw
        rest = text_lower.split(kw, 1)[-1].strip()
        parts = rest.split(" in ")
        instruction = parts[0].strip()
        time_str = parts[1].strip() if len(parts) > 1 else "60 seconds"
        seconds = 60
        if "minute" in time_str:
            num = re.search(r'\d+', time_str)
            if num: seconds = int(num.group()) * 60
        elif "second" in time_str:
            num = re.search(r'\d+', time_str)
            if num: seconds = int(num.group())
        return PCCommand(type="SCHEDULE_TASK", params={"instruction": instruction, "command": instruction, "delay": seconds})

    for kw in LIST_SCHEDULED_KEYWORDS:
        if kw in text_lower:
            return PCCommand(type="LIST_SCHEDULED_TASKS")

    # ── UIA Integration (DOM Accessibility) ───────────────────────
    for kw in UIA_CLICK_KEYWORDS:
        if text_lower.startswith(kw):
            rest = text_lower.replace(kw, "").strip()
            parts = rest.split(" in ")
            element = parts[0].strip()
            app = parts[1].strip() if len(parts) > 1 else ""
            return PCCommand(type="UIA_CLICK", params={"app_name": app, "element_name": element})
            
    for kw in UIA_TYPE_KEYWORDS:
        if text_lower.startswith(kw):
            rest = text_lower.replace(kw, "").strip()
            parts = rest.split(" in ")
            text = parts[0].strip()
            element = parts[1].strip() if len(parts) > 1 else ""
            app = parts[2].strip() if len(parts) > 2 else ""
            return PCCommand(type="UIA_TYPE", params={"app_name": app, "element_name": element, "text": text})
            
    for kw in UIA_READ_KEYWORDS:
        if text_lower.startswith(kw):
            app = text_lower.replace(kw, "").strip()
            return PCCommand(type="UIA_READ", params={"app_name": app})

    # ── Phase 1 System Commands ───────────────────────────────────────
    if cmd_type == "PROCESS_KILL":
        process_name = text_lower.replace(matched_kw, "").strip()
        return PCCommand(type="PROCESS_KILL", params={"process_name": process_name}, requires_confirmation=True)
    if cmd_type == "PROCESS_LIST":
        return PCCommand(type="PROCESS_LIST")
    if cmd_type == "DISK_INFO":
        return PCCommand(type="DISK_INFO")
    if cmd_type == "IP_ADDRESS":
        return PCCommand(type="IP_ADDRESS")
    if cmd_type == "PING":
        host = text_lower.replace(matched_kw, "").strip()
        if not host: host = "google.com"
        return PCCommand(type="PING", params={"host": host})
    if cmd_type == "AUDIO_DEVICE":
        device = text_lower.replace(matched_kw, "").strip()
        return PCCommand(type="AUDIO_DEVICE", params={"device_name": device})
    if cmd_type == "DISPLAY_SETTINGS":
        return PCCommand(type="DISPLAY_SETTINGS")
    if cmd_type == "SCREEN_RECORD":
        return PCCommand(type="SCREEN_RECORD")
    if cmd_type == "EMPTY_RECYCLE":
        return PCCommand(type="EMPTY_RECYCLE", requires_confirmation=True)
    if cmd_type == "NETWORK_STATUS":
        return PCCommand(type="NETWORK_STATUS")
    if cmd_type == "INSTALLED_APPS":
        return PCCommand(type="INSTALLED_APPS")
    if cmd_type == "STARTUP_MANAGE":
        app = text_lower.replace(matched_kw, "").strip()
        return PCCommand(type="STARTUP_MANAGE", params={"app_name": app})
    if cmd_type == "CLIPBOARD_HISTORY":
        return PCCommand(type="CLIPBOARD_HISTORY")
    if cmd_type == "HOTSPOT_TOGGLE":
        return PCCommand(type="HOTSPOT_TOGGLE")
    if cmd_type == "NIGHT_LIGHT":
        return PCCommand(type="NIGHT_LIGHT")
    if cmd_type == "DO_NOT_DISTURB":
        return PCCommand(type="DO_NOT_DISTURB")
    if cmd_type == "TASK_SCHEDULER":
        return PCCommand(type="TASK_SCHEDULER")
    if cmd_type == "SERVICE_CONTROL":
        service = text_lower.replace(matched_kw, "").strip()
        return PCCommand(type="SERVICE_CONTROL", params={"service_name": service}, requires_confirmation=True)
    if cmd_type == "POWER_PLAN":
        plan = text_lower.replace(matched_kw, "").strip()
        return PCCommand(type="POWER_PLAN", params={"plan_name": plan})
    if cmd_type == "SYSTEM_UPTIME":
        return PCCommand(type="SYSTEM_UPTIME")

    # ── MCP (Model Context Protocol) ──────────────────────────────
    if text_lower.startswith("mcp "):
        parts = text_lower[4:].split(" ", 2)
        if len(parts) >= 2:
            server = parts[0]
            tool = parts[1]
            args_str = parts[2] if len(parts) > 2 else "{}"
            import json
            try:
                args = json.loads(args_str)
            except:
                args = {"query": args_str}
            return PCCommand(type="MCP_CALL", params={"server": server, "tool": tool, "args": args})

    return None

async def parse_voice_command_async(text: str) -> Optional[PCCommand]:
    """
    Async wrapper for parse_voice_command that falls back to Groq for
    fuzzy intent classification if the Regex/Trie parser fails.
    """
    import logging
    logger = logging.getLogger("sivi.parser")
    
    # 1. Try standard deterministic parsing
    cmd = parse_voice_command(text)
    if cmd:
        return cmd
        
    # 2. If no match, ask Groq for fuzzy matching (fast)
    try:
        from core.groq_brain import groq_brain
        result = await groq_brain.classify_intent(text)
        if result:
            # Result should be [CMD: ...] format
            logger.info(f"[Parser] Groq matched intent: {result}")
            # Recursively call parse_voice_command on the newly generated tag
            return parse_voice_command(result)
    except Exception as e:
        logger.error(f"[Parser] Groq intent classification failed: {e}")
        
    return None
