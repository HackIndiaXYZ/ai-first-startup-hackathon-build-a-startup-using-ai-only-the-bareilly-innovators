"""
SIVI AI — Hindi Voice Module
Auto-detects Hindi/Hinglish input and translates to English action keywords.
Optimized with a custom Trie (Automaton) for O(N) single-pass translation.
"""

class ReplaceTrie:
    """A simple prefix trie for fast multi-phrase substring replacement."""
    def __init__(self):
        self.root = {}

    def insert(self, phrase, translation):
        node = self.root
        for char in phrase:
            if char not in node:
                node[char] = {}
            node = node[char]
        node['__trans__'] = translation

    def replace_all(self, text: str) -> str:
        """Single-pass O(N) substring replacement using the Trie."""
        result = []
        i = 0
        n = len(text)
        
        while i < n:
            node = self.root
            j = i
            last_match = None
            last_match_end = -1
            
            # Find the longest matching prefix starting at i
            while j < n and text[j] in node:
                node = node[text[j]]
                if '__trans__' in node:
                    last_match = node['__trans__']
                    last_match_end = j
                j += 1
                
            if last_match is not None:
                result.append(last_match)
                i = last_match_end + 1
            else:
                result.append(text[i])
                i += 1
                
        return "".join(result)

class HindiVoice:
    def __init__(self):
        # Hindi -> English command mapping
        self.hindi_commands = {
            # App Launcher
            "kholo": "open",
            "kholna": "open",
            "chalao": "play",
            # YouTube / Music
            "gaana bajao": "play",
            "gana bajao": "play",
            "video chalao": "play",
            # Volume
            "awaaz badhaao": "volume up",
            "awaaz badhao": "volume up",
            "awaz badhao": "volume up",
            "awaaz kam karo": "volume down",
            "awaz kam karo": "volume down",
            "awaaz band karo": "mute the volume",
            "awaz band karo": "mute the volume",
            # System
            "screen band karo": "lock screen",
            "lock karo": "lock screen",
            "band karo window": "close window",
            # News
            "kya news hai": "news",
            "news sunao": "news",
            "khabar sunao": "news",
            "samachar": "news",
            # Email
            "email bhejo": "send email",
            "mail bhejo": "send email",
            # Camera
            "photo lo": "take photo",
            "photo khicho": "take photo",
            "kya dikh raha hai": "what do you see",
            # Screen Reader
            "screen padho": "read my screen",
            "screen dekho": "read my screen",
            # File Manager
            "file banao": "create file",
            "folder banao": "create folder",
            "file dhundo": "find file",
            "file hatao": "delete file",
            # Medical
            "bukhar": "fever",
            "sir dard": "headache",
            "pet dard": "stomach ache",
            "khansi": "cough",
            "thakan": "fatigue",
        }

        # Build the O(N) Translation Trie
        self.trie = ReplaceTrie()
        for hindi, english in self.hindi_commands.items():
            self.trie.insert(hindi, english)

        # Hindi keyword markers for detection
        self.hindi_markers = {
            "karo", "khol", "kholo", "bajao", "bhejo", "sunao",
            "banao", "hatao", "dhundo", "padho", "dekho", "lo",
            "hai", "mein", "kya", "aur", "badhao", "kam",
        }

    def is_hindi(self, text: str) -> bool:
        """Check if text contains Hindi words."""
        words = text.lower().split()
        return any(w in self.hindi_markers for w in words)

    def try_translate(self, text: str) -> str:
        """
        Convert Hindi/Hinglish command to English equivalent in O(N) time.
        """
        text_lower = text.lower().strip()
        translated = self.trie.replace_all(text_lower)
        
        # Clean up extra spaces from replacements
        translated = " ".join(translated.split())
        
        if translated != text_lower:
            print(f"    Hindi -> English: '{text}' -> '{translated}'")
            return translated

        return text  # No translation needed

hindi_voice = HindiVoice()
