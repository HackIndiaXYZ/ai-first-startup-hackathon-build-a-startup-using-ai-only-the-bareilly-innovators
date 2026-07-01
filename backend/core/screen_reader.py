"""
SIVI AI  Screen Reader Module
Captures screen and analyzes with Gemini AI or OCR.
"""

import os
from PIL import ImageGrab, Image

try:
    from google import genai
except ImportError:
    genai = None


from genai_runner import run_with_key_pool

class ScreenReader:
    def __init__(self):
        self.model_name = "gemini-2.0-flash"

    def capture_screen(self) -> Image.Image:
        """Full screen capture using Pillow."""
        print(" Capturing screen...")
        return ImageGrab.grab()

    def read_screen(self, command: str = "") -> str:
        """Analyze the screen content based on the command."""
        img = self.capture_screen()

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
            def make_call(client):
                return client.models.generate_content(
                    model=self.model_name,
                    contents=[prompt, img]
                )
                
            response = run_with_key_pool(make_call)
            
            if response is None:
                return "Screen analysis failed due to quota or connection limits."
                
            return response.text.replace("*", "").replace("\n", " ").strip()
        except Exception as e:
            return f"Screen analysis failed: {e}"


screen_reader = ScreenReader()
