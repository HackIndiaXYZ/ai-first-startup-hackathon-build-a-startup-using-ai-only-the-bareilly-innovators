"""
Sivi — Voice Command Parser (PC Edition)
Parses transcribed speech text (Hinglish + English) into structured PC commands.
If no command matches, returns None so Gemini handles it as conversation.
"""

import re
from dataclasses import dataclass, field


@dataclass
class PCCommand:
    """Structured PC command parsed from voice input."""
    type: str
    params: dict = field(default_factory=dict)


# ── App Name Mappings ─────────────────────────────────────────────

APP_ALIASES = {
    # Browsers
    "chrome": "chrome", "google chrome": "chrome", "browser": "chrome",
    "firefox": "firefox", "mozilla": "firefox",
    "edge": "edge", "microsoft edge": "edge",
    "brave": "brave",
    # Communication
    "whatsapp": "whatsapp", "telegram": "telegram", "discord": "discord",
    "zoom": "zoom", "teams": "teams", "microsoft teams": "teams",
    "meet": "meet", "google meet": "meet", "skype": "skype",
    "slack": "slack",
    # Social Media
    "youtube": "youtube", "instagram": "instagram", "facebook": "facebook",
    "twitter": "twitter", "x": "twitter",
    "linkedin": "linkedin", "reddit": "reddit",
    # Media
    "spotify": "spotify", "vlc": "vlc", "media player": "media player",
    "netflix": "netflix", "prime video": "prime video",
    # Productivity
    "notepad": "notepad", "word": "word", "microsoft word": "word",
    "excel": "excel", "powerpoint": "powerpoint", "ppt": "powerpoint",
    "vs code": "vscode", "visual studio code": "vscode", "code": "vscode",
    "sublime": "sublime", "terminal": "terminal", "cmd": "cmd",
    "powershell": "powershell",
    # System
    "settings": "settings", "control panel": "control panel",
    "task manager": "task manager", "calculator": "calculator",
    "calendar": "calendar", "clock": "clock",
    "file explorer": "explorer", "explorer": "explorer",
    "paint": "paint", "snipping tool": "snipping tool",
    # Games / Others
    "steam": "steam", "epic games": "epic games",
    # Indian apps (web)
    "paytm": "paytm", "phonepe": "phonepe", "gpay": "gpay",
    "amazon": "amazon", "flipkart": "flipkart", "swiggy": "swiggy",
    "zomato": "zomato",
}

# ── Hinglish Keyword Mappings ─────────────────────────────────────

OPEN_KEYWORDS = [
    "open", "launch", "start", "run",
    "kholo", "khol do", "chalu karo", "shuru karo",
]

CLOSE_KEYWORDS = [
    "close", "quit", "exit",
    "band karo", "band kar do", "hatao",
]

VOLUME_UP_KEYWORDS = [
    "volume up", "volume badhao", "volume badha do", "awaz badhao",
    "awaaz badhao", "louder", "increase volume", "sound badhao",
]

VOLUME_DOWN_KEYWORDS = [
    "volume down", "volume kam karo", "awaz kam karo",
    "quieter", "decrease volume", "sound kam karo",
]

MUTE_KEYWORDS = [
    "mute the volume", "mute karo", "awaz band karo", "awaaz band karo",
    "silent mode",
]

SCREENSHOT_KEYWORDS = [
    "take a screenshot", "take screenshot", "screenshot le lo",
    "screen capture", "capture the screen", "ss le lo",
]

SCREEN_READ_KEYWORDS = [
    "read my screen", "screen padho", "what's on screen",
    "summarize screen", "screen batao", "what's on my screen",
]

LOCK_KEYWORDS = [
    "lock the screen", "lock screen", "screen lock",
    "lock karo", "lock kar do",
]

SHUTDOWN_KEYWORDS = [
    "shutdown the computer", "shut down the computer",
    "band karo computer", "computer band karo", "pc band karo",
    "turn off computer", "turn off the pc",
]

RESTART_KEYWORDS = [
    "restart the computer", "reboot the computer",
    "restart karo", "reboot karo", "computer restart karo",
]

SLEEP_KEYWORDS = [
    "sleep mode", "put to sleep", "so jao computer",
    "sleep karo computer", "computer ko sleep karo",
]

BRIGHTNESS_UP_KEYWORDS = [
    "brightness up", "brightness badhao", "make it brighter",
    "screen bright karo", "roshan karo", "increase brightness",
]

BRIGHTNESS_DOWN_KEYWORDS = [
    "brightness down", "brightness kam karo", "make it dimmer",
    "screen dim karo", "andhera karo", "decrease brightness",
]

PLAY_KEYWORDS = [
    "play", "chalao", "bajao", "suno",
]

SEARCH_KEYWORDS = [
    "search for", "search", "google", "search karo", "dhundho",
]

TYPE_KEYWORDS = [
    "type", "likho", "likh do",
]

FILE_CREATE_KEYWORDS = ["create file", "file banao", "naya file"]
FILE_DELETE_KEYWORDS = ["delete file", "file delete karo", "file hatao"]
FOLDER_CREATE_KEYWORDS = ["create folder", "folder banao", "naya folder"]
FIND_FILE_KEYWORDS = ["find file", "file dhundho", "file khojo"]
LIST_FILES_KEYWORDS = ["list files in", "list files"]
LIST_WINDOWS_KEYWORDS = ["what apps are open", "what windows are open", "read browsers", "read active apps", "show open apps", "check open apps"]
READ_CLIPBOARD_KEYWORDS = ["read clipboard", "what's on clipboard", "clipboard batao"]
WRITE_CLIPBOARD_KEYWORDS = ["copy this to clipboard"]
MEDIA_PLAY_PAUSE_KEYWORDS = ["play media", "pause media", "play music", "pause music", "stop music", "resume music", "play video", "pause video"]
MEDIA_NEXT_KEYWORDS = ["next track", "next song", "next video", "skip song"]
MEDIA_PREV_KEYWORDS = ["previous track", "previous song", "previous video", "last song"]

SYSTEM_STATUS_KEYWORDS = ["system status", "pc health", "check system", "system kaisa hai", "what time is it", "current time", "what is the date", "aaj ki date", "time kya ho raha hai", "time kya hai"]
REMEMBER_KEYWORDS = ["remember", "yaad rakho", "memorize"]
FORGET_KEYWORDS = ["forget all", "clear memory", "yaad bhool jao"]
EMOTION_ANALYSIS_KEYWORDS = ["how do i look", "read my face", "check my mood", "mera mood kaisa hai", "analyze my emotion", "meri shakal dekho"]
DESCRIBE_SCENE_KEYWORDS = ["take photo", "what do you see"]
SWITCH_MODE_KEYWORDS = ["switch mode to", "change mode to", "switch personality to"]

MINIMIZE_KEYWORDS = ["minimize", "chota karo"]
MAXIMIZE_KEYWORDS = ["maximize", "bada karo"]
CALENDAR_KEYWORDS = ["calendar", "schedule", "my events", "today's events", "what's scheduled"]
MEDICAL_KEYWORDS = ["health", "medical", "headache", "fever", "bukhar", "sir dard", "pet dard", "khansi", "thakan", "cough", "stomach"]
EMAIL_KEYWORDS = ["send email"]
WHATSAPP_KEYWORDS = ["send message", "send msg"]
PRESS_KEYWORDS = ["press"]

# ── Mouse Keywords ────────────────────────────────────────────────
MOUSE_CLICK_KEYWORDS = ["mouse click", "left click", "right click", "double click"]
MOUSE_SCROLL_KEYWORDS = ["scroll up", "scroll down"]
MOUSE_MOVE_KEYWORDS = ["move mouse up", "move mouse down", "move mouse left", "move mouse right"]


# ── Developer Keywords ────────────────────────────────────────────
DEV_CMD_KEYWORDS = ["run command", "execute terminal", "run terminal"]
DEV_GIT_STATUS_KEYWORDS = ["git status", "check git", "check repository"]
DEV_KILL_PORT_KEYWORDS = ["kill port", "stop port"]
DEV_ANALYZE_CODE_KEYWORDS = ["analyze code in", "check bugs in", "find bugs in"]
DEV_GENERATE_CODE_KEYWORDS = ["write code for", "generate code for"]
DEV_OPEN_EDITOR_KEYWORDS = ["open in editor", "open in vs code", "open in vscode"]
DEV_CLOSE_EDITOR_KEYWORDS = ["close current file", "close editor tab", "band karo tab"]


# Cache for compiled regex patterns
_compiled_patterns = {}

def _exact_phrase(text_lower: str, keywords: list) -> bool:
    """
    Check if any keyword appears as a complete phrase (not substring of another word).
    Optimized: Uses a single combined regex pattern and caches it for O(1) repeated lookups.
    """
    key = tuple(keywords)
    if key not in _compiled_patterns:
        # Join all keywords with OR (|), escape them, and wrap in word boundaries
        pattern = r'(?<!\w)(?:' + '|'.join(re.escape(kw) for kw in keywords) + r')(?!\w)'
        _compiled_patterns[key] = re.compile(pattern)
        
    return bool(_compiled_patterns[key].search(text_lower))


import string

def parse_command(text: str) -> "PCCommand | None":
    """
    Parse voice transcription text into a PCCommand.
    Returns None if no command pattern matches (let Gemini handle it).
    """
    if not text or not text.strip():
        return None

    # Fast-path for exact technical tags (e.g. if Sivi outputs [CMD: WIFI_ON])
    text_upper = text.strip().upper()
    VALID_NO_PARAM_TYPES = {
        "SHUTDOWN", "RESTART", "SLEEP", "VOLUME_UP", "VOLUME_DOWN", "MUTE", 
        "BRIGHTNESS_UP", "BRIGHTNESS_DOWN", "SCREENSHOT", "READ_SCREEN", "LOCK_SCREEN", 
        "WIFI_ON", "WIFI_OFF", "BLUETOOTH_ON", "BLUETOOTH_OFF", "MEDIA_PLAY_PAUSE", 
        "MEDIA_NEXT", "MEDIA_PREV", "READ_CLIPBOARD", "NEWS", "SYSTEM_STATUS", 
        "READ_WINDOWS", "FORGET_ALL", "ANALYZE_EMOTION", "DESCRIBE_SCENE", "DEV_GIT_STATUS"
    }
    if text_upper in VALID_NO_PARAM_TYPES:
        return PCCommand(type=text_upper)

    # Strip punctuation and convert to lowercase
    text_lower = text.lower().strip()
    
    # Remove ALL quotes to prevent parsing errors when Sivi quotes parameters
    text_lower = text_lower.replace('"', '').replace("'", "")

    # Remove standard punctuation at the end of the sentence
    while text_lower and text_lower[-1] in string.punctuation:
        text_lower = text_lower[:-1]
    
    text_lower = text_lower.strip()

    # ── Open App ──────────────────────────────────────────────────
    for kw in OPEN_KEYWORDS:
        # Must start with keyword followed by a space then the app name
        if text_lower.startswith(kw + " "):
            app_name = text_lower[len(kw):].strip()
            if app_name:
                resolved = APP_ALIASES.get(app_name, app_name)
                return PCCommand(type="OPEN_APP", params={"app_name": resolved, "raw": app_name})

    # ── Shutdown / Restart / Sleep (check BEFORE close/sleep words) ──
    # Use full phrase matching to avoid "sleep" matching conversational speech
    if _exact_phrase(text_lower, SHUTDOWN_KEYWORDS):
        return PCCommand(type="SHUTDOWN")

    if _exact_phrase(text_lower, RESTART_KEYWORDS):
        return PCCommand(type="RESTART")

    if _exact_phrase(text_lower, SLEEP_KEYWORDS):
        return PCCommand(type="SLEEP")

    # ── Close App ─────────────────────────────────────────────────
    for kw in CLOSE_KEYWORDS:
        if text_lower.startswith(kw + " ") or text_lower == kw:
            app_name = text_lower[len(kw):].strip()
            return PCCommand(type="CLOSE_APP", params={"app_name": app_name})

    # ── Volume ────────────────────────────────────────────────────
    if _exact_phrase(text_lower, VOLUME_UP_KEYWORDS):
        return PCCommand(type="VOLUME_UP")

    if _exact_phrase(text_lower, VOLUME_DOWN_KEYWORDS):
        return PCCommand(type="VOLUME_DOWN")

    # Mute: use full-phrase matching to avoid "commute", "compute" etc.
    if _exact_phrase(text_lower, MUTE_KEYWORDS):
        return PCCommand(type="MUTE")

    # ── Brightness ────────────────────────────────────────────────
    if _exact_phrase(text_lower, BRIGHTNESS_UP_KEYWORDS):
        return PCCommand(type="BRIGHTNESS_UP")

    if _exact_phrase(text_lower, BRIGHTNESS_DOWN_KEYWORDS):
        return PCCommand(type="BRIGHTNESS_DOWN")

    # ── Screenshot ────────────────────────────────────────────────
    if _exact_phrase(text_lower, SCREENSHOT_KEYWORDS):
        return PCCommand(type="SCREENSHOT")

    # ── Screen Reader ─────────────────────────────────────────────
    if _exact_phrase(text_lower, SCREEN_READ_KEYWORDS):
        return PCCommand(type="READ_SCREEN")

    # ── Lock Screen ───────────────────────────────────────────────
    if _exact_phrase(text_lower, LOCK_KEYWORDS):
        return PCCommand(type="LOCK_SCREEN")

    # ── WiFi / Bluetooth Toggle ───────────────────────────────────
    if re.search(r'\bwifi\b|\bwi-fi\b|\binternet\b', text_lower):
        if re.search(r'\bon\b|\bchalu\b', text_lower):
            return PCCommand(type="WIFI_ON")
        elif re.search(r'\boff\b|\bband\b', text_lower):
            return PCCommand(type="WIFI_OFF")

    if re.search(r'\bbluetooth\b|\bbt\b', text_lower):
        if re.search(r'\bon\b|\bchalu\b', text_lower):
            return PCCommand(type="BLUETOOTH_ON")
        elif re.search(r'\boff\b|\bband\b', text_lower):
            return PCCommand(type="BLUETOOTH_OFF")

    # ── Media Controls ────────────────────────────────────────────
    for kw in MEDIA_PLAY_PAUSE_KEYWORDS:
        if kw in text_lower:
            return PCCommand(type="MEDIA_PLAY_PAUSE")

    for kw in MEDIA_NEXT_KEYWORDS:
        if kw in text_lower:
            return PCCommand(type="MEDIA_NEXT")

    for kw in MEDIA_PREV_KEYWORDS:
        if kw in text_lower:
            return PCCommand(type="MEDIA_PREV")

    # ── Play on YouTube / Spotify ─────────────────────────────────
    for kw in PLAY_KEYWORDS:
        if text_lower.startswith(kw + " "):
            query = text_lower[len(kw):].strip()
            if query:
                if "spotify" in text_lower:
                    return PCCommand(type="PLAY_SPOTIFY", params={"query": query.replace("on spotify", "").strip()})
                return PCCommand(type="PLAY_YOUTUBE", params={"query": query})

    # ── Google Search ─────────────────────────────────────────────
    for kw in SEARCH_KEYWORDS:
        if text_lower.startswith(kw + " "):
            query = text_lower[len(kw):].strip()
            if query:
                return PCCommand(type="SEARCH", params={"query": query})

    # ── Type Text ─────────────────────────────────────────────────
    for kw in TYPE_KEYWORDS:
        if text_lower.startswith(kw + " "):
            content = text.strip()[len(kw):].strip()  # preserve original case
            if content:
                content = content.strip(' "\'') # Remove LLM hallucinated quotes
                return PCCommand(type="TYPE_TEXT", params={"text": content})

    # ── Keyboard Press ────────────────────────────────────────────
    for kw in PRESS_KEYWORDS:
        if text_lower.startswith(kw + " "):
            key = text_lower[len(kw):].strip()
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
            # Extract number from the text if present
            amt_match = re.search(r'\b(\d+)\b', text_lower)
            amount = int(amt_match.group(1)) if amt_match else 200
            return PCCommand(type="MOUSE_MOVE", params={"direction": direction, "amount": amount})
            
    if "move mouse to" in text_lower:
        coords = re.findall(r'\b(\d+)\b', text_lower)
        if len(coords) >= 2:
            return PCCommand(type="MOUSE_MOVE_TO", params={"x": int(coords[0]), "y": int(coords[1])})


    # ── File Operations ───────────────────────────────────────────
    for kw in FILE_CREATE_KEYWORDS:
        if kw in text_lower:
            name = text_lower.replace(kw, "").strip()
            if name:
                return PCCommand(type="CREATE_FILE", params={"name": name})

    for kw in FILE_DELETE_KEYWORDS:
        if kw in text_lower:
            name = text_lower.replace(kw, "").strip()
            if name:
                return PCCommand(type="DELETE_FILE", params={"name": name})

    for kw in FOLDER_CREATE_KEYWORDS:
        if kw in text_lower:
            name = text_lower.replace(kw, "").strip()
            if name:
                return PCCommand(type="CREATE_FOLDER", params={"name": name})

    for kw in FIND_FILE_KEYWORDS:
        if kw in text_lower:
            name = text_lower.replace(kw, "").strip()
            if name:
                return PCCommand(type="FIND_FILE", params={"name": name})

    for kw in LIST_FILES_KEYWORDS:
        if text_lower.startswith(kw):
            folder = text_lower.replace(kw, "").strip()
            return PCCommand(type="LIST_FILES", params={"folder": folder})

    for kw in LIST_WINDOWS_KEYWORDS:
        if kw in text_lower:
            return PCCommand(type="READ_WINDOWS")

    for kw in READ_CLIPBOARD_KEYWORDS:
        if kw in text_lower:
            return PCCommand(type="READ_CLIPBOARD")

    for kw in WRITE_CLIPBOARD_KEYWORDS:
        if text_lower.startswith(kw):
            content = text.strip()[len(kw):].strip()
            return PCCommand(type="WRITE_CLIPBOARD", params={"text": content})


    # ── News ──────────────────────────────────────────────────────
    if re.search(r'\bnews\b|\bheadlines\b|\bkhabar\b', text_lower):
        return PCCommand(type="NEWS")

    # ── System Monitor ────────────────────────────────────────────
    for kw in SYSTEM_STATUS_KEYWORDS:
        if kw in text_lower:
            return PCCommand(type="SYSTEM_STATUS")

    # ── Memory Vault ──────────────────────────────────────────────
    for kw in REMEMBER_KEYWORDS:
        if kw in text_lower:
            fact = text_lower.replace(kw, "").strip()
            if fact:
                return PCCommand(type="REMEMBER", params={"fact": fact})

    for kw in FORGET_KEYWORDS:
        if kw in text_lower:
            return PCCommand(type="FORGET_ALL")

    # ── Camera Vision (Emotion / Scene) ───────────────────────────
    for kw in EMOTION_ANALYSIS_KEYWORDS:
        if kw in text_lower:
            return PCCommand(type="ANALYZE_EMOTION")

    for kw in DESCRIBE_SCENE_KEYWORDS:
        if kw in text_lower:
            return PCCommand(type="DESCRIBE_SCENE")

    for kw in SWITCH_MODE_KEYWORDS:
        if kw in text_lower:
            mode = text_lower.replace(kw, "").strip()
            # Map common spoken phrases to actual mode keys
            if "professional" in mode or "pro" in mode: mode = "professional"
            elif "assistant" in mode: mode = "assistant"
            elif "developer" in mode or "dev" in mode: mode = "developer"
            else: mode = "gf"
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
    for kw in CALENDAR_KEYWORDS:
        if kw in text_lower:
            if "create" in text_lower or "add" in text_lower or "schedule" in text_lower:
                for prefix in ["schedule ", "create event ", "add event ", "add to calendar "]:
                    if prefix in text_lower:
                        title = text_lower.split(prefix, 1)[-1].strip()
                        return PCCommand(type="CREATE_EVENT", params={"title": title})
                return PCCommand(type="CREATE_EVENT", params={"title": ""})
            return PCCommand(type="CALENDAR_EVENTS")

    # ── Medical ───────────────────────────────────────────────────
    for kw in MEDICAL_KEYWORDS:
        if kw in text_lower:
            return PCCommand(type="MEDICAL_ADVICE", params={"query": text_lower})

    # ── Email ─────────────────────────────────────────────────────
    for kw in EMAIL_KEYWORDS:
        if text_lower.startswith(kw):
            parts = text_lower.split("saying")
            to = parts[0].replace(kw + " to", "").replace(kw, "").strip()
            content = parts[1].strip() if len(parts) > 1 else ""
            return PCCommand(type="SEND_EMAIL", params={"to": to, "content": content})

    # ── WhatsApp ──────────────────────────────────────────────────
    for kw in WHATSAPP_KEYWORDS:
        if text_lower.startswith(kw):
            parts = text_lower.split("saying")
            number = parts[0].replace(kw + " to", "").replace(kw, "").strip()
            content = parts[1].strip() if len(parts) > 1 else ""
            return PCCommand(type="SEND_WHATSAPP", params={"number": number, "content": content})

    # ── Developer Commands ────────────────────────────────────────
    for kw in DEV_CMD_KEYWORDS:
        if kw in text_lower:
            cmd_str = text_lower.replace(kw, "").strip()
            if cmd_str:
                return PCCommand(type="DEV_RUN_CMD", params={"command": cmd_str})

    for kw in DEV_GIT_STATUS_KEYWORDS:
        if kw in text_lower:
            return PCCommand(type="DEV_GIT_STATUS")

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
            # Parse like: "write code for [instructions] in [filename]"
            parts = text_lower.replace(kw, "").split(" in ")
            instructions = parts[0].strip()
            filename = parts[1].strip() if len(parts) > 1 else "output.txt"
            return PCCommand(type="DEV_GENERATE_CODE", params={"filename": filename, "instructions": instructions})

    for kw in DEV_OPEN_EDITOR_KEYWORDS:
        if kw in text_lower:
            filename = text_lower.replace(kw, "").strip()
            return PCCommand(type="DEV_OPEN_EDITOR", params={"filename": filename})

    for kw in DEV_CLOSE_EDITOR_KEYWORDS:
        if kw in text_lower:
            return PCCommand(type="DEV_CLOSE_EDITOR")

    # ── No match — let Gemini handle it as conversation ───────────
    return None
