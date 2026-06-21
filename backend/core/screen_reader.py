"""
TITAN AI  Screen Reader Module
Captures screen and analyzes with Gemini AI or OCR.
"""

import os
from PIL import ImageGrab, Image

try:
    from google import genai
except ImportError:
    genai = None


import json

def _get_api_key():
    key = os.getenv("GEMINI_API_KEY")
    if key: return key
    try:
        settings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sivi_settings.json")
        with open(settings_path, "r") as f:
            return json.load(f).get("api_key")
    except Exception:
        return None

class ScreenReader:
    def __init__(self):
        self.model_name = "gemini-flash-latest"

    def _get_client(self):
        if not genai: return None
        key = _get_api_key()
        return genai.Client(api_key=key) if key else None

    def capture_screen(self) -> Image.Image:
        """Full screen capture using Pillow."""
        print(" Capturing screen...")
        return ImageGrab.grab()

    def read_screen(self, command: str = "") -> str:
        """Analyze the screen content based on the command."""
        img = self.capture_screen()
        client = self._get_client()

        if not client:
            return "Screen reader offline. Gemini API key not configured."

        # Pick the right prompt based on command
        if "summarize" in command:
            prompt = "Summarize what you see on this computer screen in 2 sentences."
        elif "read this text" in command:
            prompt = "Extract and read all the text visible on this screen. Return only the text content."
        elif "what app" in command:
            prompt = "What application is currently active on this screen? Just name the app."
        else:
            prompt = "Describe what you see on this computer screen concisely, as if you are an AI assistant named Sivi."

        try:
            print(" Analyzing screen with Gemini...")
            response = client.models.generate_content(
                model=self.model_name,
                contents=[prompt, img]
            )
            return response.text.replace("*", "").replace("\n", " ").strip()
        except Exception as e:
            return f"Screen analysis failed: {e}"


screen_reader = ScreenReader()
