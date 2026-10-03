"""
SIVI AI -- Hindi Voice Module
Auto-detects Hindi/Hinglish input and translates to English action keywords.
Optimized with a custom Trie (Automaton) for O(N) single-pass translation.

Improvements v2:
  - Word-boundary aware matching (avoids "lo" matching inside "hello")
  - Massively expanded Hindi dictionary covering all 80+ Sivi commands
  - Phonetic normalization for common Hinglish mispronunciations
"""


class ReplaceTrie:
    """
    Prefix Trie for fast multi-phrase substring replacement.
    O(N) single-pass scanning across the input text.
    Only matches at word boundaries to prevent false positives.
    """

    def __init__(self):
        self.root = {}

    def insert(self, phrase: str, translation: str):
        node = self.root
        for char in phrase:
            if char not in node:
                node[char] = {}
            node = node[char]
        node["__trans__"] = translation

    def replace_all(self, text: str) -> str:
        """
        Single-pass O(N) word-boundary-aware replacement.
        Only replaces phrases that start and end at word boundaries (space or string edge).
        """
        result = []
        i = 0
        n = len(text)

        while i < n:
            # Check word boundary: only try to match at start of text or after a space
            at_word_start = (i == 0 or text[i - 1] == " ")

            if at_word_start:
                node = self.root
                j = i
                last_match = None
                last_match_end = -1

                # Find the longest phrase starting at i
                while j < n and text[j] in node:
                    node = node[text[j]]
                    if "__trans__" in node:
                        # Validate word boundary at end of match
                        at_word_end = (j + 1 == n or text[j + 1] == " ")
                        if at_word_end:
                            last_match = node["__trans__"]
                            last_match_end = j
                    j += 1

                if last_match is not None:
                    result.append(last_match)
                    i = last_match_end + 1
                    # Skip trailing space after match
                    if i < n and text[i] == " ":
                        result.append(" ")
                        i += 1
                    continue

            result.append(text[i])
            i += 1

        return "".join(result)


# ── Phonetic normalization map ────────────────────────────────────────────────
# Correct common mispronunciations BEFORE Trie translation
_PHONETIC_FIXES = {
    "watsapp": "whatsapp",
    "whatsup": "whatsapp",
    "wotsapp": "whatsapp",
    "spotifai": "spotify",
    "youtoob": "youtube",
    "yotube": "youtube",
    "kroam": "chrome",
    "krome": "chrome",
    "diskord": "discord",
    "telegaram": "telegram",
    "telagarm": "telegram",
    "eksel": "excel",
    "notepaid": "notepad",
    "powerpoint": "powerpoint",
    "vizual studio": "visual studio code",
}


class HindiVoice:
    def __init__(self):
        # ── Comprehensive Hindi -> English command mapping ──────────────────────
        self.hindi_commands = {
            # ── App Launcher ──────────────────────────────────────────────────
            "kholo": "open",
            "kholna": "open",
            "khol do": "open",
            "chalu karo": "open",
            "shuru karo": "open",
            "band karo": "close",
            "band kar do": "close",
            "hatao": "close",

            # ── Media Playback ────────────────────────────────────────────────
            "chalao": "play",
            "bajao": "play",
            "suno": "play",
            "gaana bajao": "play",
            "gana bajao": "play",
            "video chalao": "play",
            "music bajao": "play music",
            "paused karo": "pause media",
            "roko": "pause media",
            "band karo music": "stop music",
            "agle gaane": "next track",
            "agle gaana": "next track",
            "pichla gaana": "previous track",
            "pichle gaana": "previous track",

            # ── Volume ────────────────────────────────────────────────────────
            "awaaz badhaao": "volume up",
            "awaaz badhao": "volume up",
            "awaz badhao": "volume up",
            "sound badhao": "volume up",
            "louder karo": "volume up",
            "awaaz kam karo": "volume down",
            "awaz kam karo": "volume down",
            "sound kam karo": "volume down",
            "quieter karo": "volume down",
            "awaaz band karo": "mute the volume",
            "awaz band karo": "mute the volume",
            "silent karo": "mute the volume",
            "mute karo": "mute the volume",

            # ── Brightness ───────────────────────────────────────────────────
            "brightness badhao": "brightness up",
            "roshan karo": "brightness up",
            "screen bright karo": "brightness up",
            "brightness kam karo": "brightness down",
            "andhera karo": "brightness down",
            "screen dim karo": "brightness down",

            # ── System ───────────────────────────────────────────────────────
            "screen band karo": "lock screen",
            "lock karo": "lock screen",
            "lock kar do": "lock screen",
            "screenshot le lo": "take screenshot",
            "screenshot lelo": "take screenshot",
            "ss le lo": "take screenshot",
            "band karo computer": "shutdown the computer",
            "computer band karo": "shutdown the computer",
            "pc band karo": "shutdown the computer",
            "computer restart karo": "restart the computer",
            "restart karo": "restart the computer",
            "computer ko sleep karo": "sleep mode",
            "so jao computer": "sleep mode",
            "phir milenge": "goodbye",
            "alvida": "goodbye",

            # ── File Operations ───────────────────────────────────────────────
            "file banao": "create file",
            "naya file": "create file",
            "file banao naam": "create file",
            "folder banao": "create folder",
            "naya folder": "create folder",
            "file hatao": "delete file",
            "file delete karo": "delete file",
            "folder hatao": "delete folder",
            "folder delete karo": "delete folder",
            "file dhundo": "find file",
            "file khojo": "find file",
            "file dhundho": "find file",
            "file kholo": "open file",
            "open the file": "open file",

            # ── Search ────────────────────────────────────────────────────────
            "dhundho": "search",
            "search karo": "search for",
            "google karo": "search for",

            # ── WhatsApp ──────────────────────────────────────────────────────
            "message bhejo": "send message",
            "message bhej do": "send message",
            "whatsapp pe bhej": "send message",
            "whatsapp karo": "send message",
            "naya message padho": "read whatsapp",
            "unread message padho": "read whatsapp",
            "messages padho": "read whatsapp",
            "whatsapp check karo": "read whatsapp",

            # ── Email ─────────────────────────────────────────────────────────
            "email bhejo": "send email",
            "mail bhejo": "send email",

            # ── News ──────────────────────────────────────────────────────────
            "kya news hai": "news",
            "news sunao": "news",
            "khabar sunao": "news",
            "samachar sunao": "news",
            "aaj ki news": "news",
            "kya hua aaj": "news",

            # ── Camera / Vision ───────────────────────────────────────────────
            "photo lo": "take photo",
            "photo khicho": "take photo",
            "kya dikh raha hai": "what do you see",
            "dekho kya hai": "what do you see",
            "mujhe dekho": "analyze my emotion",
            "mera mood batao": "check my mood",
            "mood batao": "check my mood",
            "meri shakal dekho": "read my face",

            # ── Screen Reader ─────────────────────────────────────────────────
            "screen padho": "read my screen",
            "screen dekho": "read my screen",
            "screen pe kya hai": "what's on screen",
            "screen batao": "what's on screen",

            # ── Memory ───────────────────────────────────────────────────────
            "yaad rakho": "remember",
            "yaad karo": "remember",
            "memory clear karo": "forget all",
            "sab bhool jao": "forget all",
            "yaad bhool jao": "forget all",

            # ── Weather ───────────────────────────────────────────────────────
            "mausam kaisa hai": "get weather",
            "mausam batao": "get weather",
            "aaj ka mausam": "get weather",

            # ── Calendar ─────────────────────────────────────────────────────
            "aaj kya schedule hai": "calendar",
            "meri meetings": "calendar",
            "aaj ki meetings": "calendar",

            # ── Windows / Apps ────────────────────────────────────────────────
            "window chota karo": "minimize",
            "minimize karo": "minimize",
            "window bada karo": "maximize",
            "maximize karo": "maximize",
            "konse apps khule hain": "what apps are open",
            "khule apps batao": "what apps are open",

            # ── Clipboard ────────────────────────────────────────────────────
            "clipboard kya hai": "what's on clipboard",
            "clipboard batao": "what's on clipboard",
            "clipboard mein copy karo": "copy this to clipboard",

            # ── Timer ────────────────────────────────────────────────────────
            "timer lagao": "set timer for",
            "alarm lagao": "set alarm for",
            "yaad dilao": "remind me in",

            # ── Developer ────────────────────────────────────────────────────
            "terminal mein chalao": "run command",
            "code check karo": "check git",
            "tests chalao": "run tests",
            "port band karo": "kill port",

            # ── Wellness ─────────────────────────────────────────────────────
            "sehat kaisi hai": "wellness check",
            "aankhein thak gayi": "eye strain",
            "posture dekho": "posture check",

            # ── Medical ───────────────────────────────────────────────────────
            "bukhar": "fever",
            "sir dard": "headache",
            "pet dard": "stomach ache",
            "khansi": "cough",
            "thakan": "fatigue",

            # ── Swarm / Background Tasks ──────────────────────────────────────
            "background research karo": "research in background",
            "background mein chalao": "assign background task",

            # ── Phone Handoff ─────────────────────────────────────────────────
            "phone pe bhejo": "send to phone",
            "phone pe alert karo": "alert me on phone",
        }

        # Build the Trie from the dictionary
        self.trie = ReplaceTrie()
        for hindi, english in self.hindi_commands.items():
            self.trie.insert(hindi, english)

        # Fast set for detection: is this possibly Hindi?
        self.hindi_markers = {
            "karo", "kar", "khol", "kholo", "bajao", "bhejo", "sunao",
            "banao", "hatao", "dhundo", "dhundho", "padho", "dekho",
            "hai", "mein", "kya", "aur", "badhao", "kam", "band",
            "naya", "lo", "dalo", "roko", "chalao", "bhej", "bhejdo",
            "yaad", "bhool", "padh", "check", "batao", "kaisa", "aaj",
        }

    def is_hindi(self, text: str) -> bool:
        """Return True if the text likely contains a Hindi/Hinglish word."""
        words = set(text.lower().split())
        return bool(words & self.hindi_markers)

    def _apply_phonetic_fixes(self, text: str) -> str:
        """Correct common mispronunciations before translation."""
        for wrong, correct in _PHONETIC_FIXES.items():
            text = text.replace(wrong, correct)
        return text

    def try_translate(self, text: str) -> str:
        """
        Convert Hindi/Hinglish command to English equivalent in O(N) time.
        Returns the (possibly modified) text.
        """
        text_lower = text.lower().strip()

        # Step 1: phonetic normalization
        text_lower = self._apply_phonetic_fixes(text_lower)

        # Step 2: Trie-based multi-phrase replacement (single pass, word-boundary aware)
        translated = self.trie.replace_all(text_lower)

        # Step 3: normalize whitespace
        translated = " ".join(translated.split())

        if translated != text_lower:
            print(f"    Hindi -> English: '{text}' -> '{translated}'")
            return translated

        return text  # No translation needed


hindi_voice = HindiVoice()
