"""
TITAN AI — Hindi Voice Module
Auto-detects Hindi/Hinglish input and translates to English action keywords.
"""


class HindiVoice:
    def __init__(self):
        # Hindi -> English command mapping
        self.hindi_commands = {
            # App Launcher
            "kholo": "open",
            "kholna": "open",
            # NOTE: "chalao" means "play/run", NOT "open"
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

        # Hindi keyword markers for detection
        self.hindi_markers = [
            "karo", "khol", "kholo", "bajao", "bhejo", "sunao",
            "banao", "hatao", "dhundo", "padho", "dekho", "lo",
            "hai", "mein", "kya", "aur", "badhao", "kam",
        ]

    def is_hindi(self, text: str) -> bool:
        """Check if text contains Hindi words."""
        words = text.lower().split()
        hindi_count = sum(1 for w in words if w in self.hindi_markers)
        return hindi_count >= 1

    def try_translate(self, text: str) -> str:
        """
        Attempt to convert Hindi/Hinglish command to English equivalent.
        Returns the original text if no translation found.
        Longest match wins to avoid partial replacements.
        """
        text_lower = text.lower().strip()

        # Sort by phrase length descending so longer phrases match first
        for hindi, english in sorted(self.hindi_commands.items(), key=lambda x: -len(x[0])):
            if hindi in text_lower:
                remainder = text_lower.replace(hindi, "").strip()
                result = f"{english} {remainder}".strip() if remainder else english
                print(f"    Hindi -> English: '{text}' -> '{result}'")
                return result

        return text  # No translation needed


hindi_voice = HindiVoice()
