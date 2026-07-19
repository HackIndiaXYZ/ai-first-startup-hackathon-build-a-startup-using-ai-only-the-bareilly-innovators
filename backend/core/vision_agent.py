"""
SIVI AI — Vision Agent
Leverages Gemini 2.0 Flash for extremely fast spatial reasoning
to find the X, Y coordinates of UI elements on the screen.
"""

import os
import re
import asyncio
import threading
from dotenv import load_dotenv
import pyautogui
from PIL import ImageGrab, Image

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

from genai_runner import run_with_key_pool


class VisionAgent:
    def __init__(self):
        # Dedicated event loop in a background thread — avoids deadlocking uvicorn's loop
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="VisionAgentLoop")
        self._thread.start()

    def _run_loop(self):
        """Run the dedicated event loop forever in a background thread."""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _run_async(self, coro, timeout=30):
        """Schedule a coroutine on the dedicated loop and block until done."""
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    async def _async_find_ui_element(self, target_description: str, img: Image.Image = None) -> tuple[int, int]:
        if img is None:
            try:
                img = ImageGrab.grab()
            except Exception as e:
                print("=========================================================")
                print(" ERROR: VISION AGENT FAILED TO CAPTURE SCREEN")
                print(" Please check OS permissions for screen recording.")
                print("=========================================================")
                return None

        prompt = f"""Find the bounding box of this exact UI element: "{target_description}"
Respond ONLY with a JSON array of 4 integers scaled to 1000: [ymin, xmin, ymax, xmax].
Do not output any markdown. Just the array.
If the element is absolutely nowhere on the screen, respond exactly with: None"""

        try:
            print(f" Vision Agent analyzing screen for: {target_description}...")
            
            def make_call(client):
                return client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[img, prompt],
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                    )
                )

            # run_with_key_pool is synchronous, safe to call from any thread
            response = run_with_key_pool(make_call)
            
            if response is None:
                return None

            
            text = response.text.strip()
            
            if "None" in text:
                print(f" Vision Agent could not find: {target_description}")
                return None
                
            # Extract [ymin, xmin, ymax, xmax]
            match = re.search(r'\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]', text)
            if not match:
                print(f" Vision Agent returned invalid format: {text}")
                return None
                
            ymin, xmin, ymax, xmax = map(int, match.groups())
            
            # Calculate the center point in the 0-1000 normalized space
            center_x_norm = (xmin + xmax) / 2.0
            center_y_norm = (ymin + ymax) / 2.0
            
            # Get the logical screen dimensions from pyautogui
            screen_width, screen_height = pyautogui.size()
            
            # Scale to actual logical screen coordinates
            click_x = int((center_x_norm / 1000.0) * screen_width)
            click_y = int((center_y_norm / 1000.0) * screen_height)
            
            print(f" Vision Agent located '{target_description}' at ({click_x}, {click_y})")
            return (click_x, click_y)
            
        except Exception as e:
            print(f" Vision Agent failed: {e}")
            return None

    def find_ui_element(self, target_description: str, img: Image.Image = None) -> tuple[int, int]:
        """
        Synchronous wrapper — safe to call from ANY thread (WhatsApp, bridge, etc.)
        Uses a dedicated background loop so it never deadlocks uvicorn.
        """
        return self._run_async(self._async_find_ui_element(target_description, img))

    async def _async_analyze_screen(self, prompt: str, img: Image.Image = None) -> str:
        """Analyzes the screen and returns Gemini's text response."""
        if img is None:
            try:
                img = ImageGrab.grab()
            except Exception as e:
                print(f" Vision Agent failed to capture screen: {e}")
                return "Error: Could not capture screen."

        try:
            print(f" Vision Agent analyzing screen text...")
            
            def make_call(client):
                return client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[img, prompt],
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                    )
                )

            response = run_with_key_pool(make_call)
            
            if response is None:
                return "Error: Vision API returned no response."

            return response.text.strip()
            
        except Exception as e:
            print(f" Vision Agent analysis failed: {e}")
            return f"Error: Vision Agent failed - {e}"

    def analyze_screen(self, prompt: str, img: Image.Image = None) -> str:
        """
        Synchronous wrapper for analyze_screen.
        """
        return self._run_async(self._async_analyze_screen(prompt, img))

vision_agent = VisionAgent()

