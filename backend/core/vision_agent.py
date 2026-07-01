"""
SIVI AI — Vision Agent
Leverages Gemini 2.0 Flash for extremely fast spatial reasoning
to find the X, Y coordinates of UI elements on the screen.
"""

import os
import re
import asyncio
from dotenv import load_dotenv
import pyautogui
from PIL import ImageGrab, Image
from google import genai
from google.genai import types
from genai_runner import run_with_key_pool

class VisionAgent:
    def __init__(self):
        pass

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
            
            # Use run_in_executor to avoid blocking the event loop with synchronous Gemini call
            loop = asyncio.get_event_loop()
            
            def make_call(client):
                return client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[img, prompt],
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                    )
                )

            response = await loop.run_in_executor(None, lambda: run_with_key_pool(make_call))
            
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
        Synchronous wrapper for legacy code compatibility (e.g. whatsapp_desktop_controller).
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            # If we're already in an async context but calling the sync wrapper
            # (which happens in whatsapp_desktop_controller's Thread)
            future = asyncio.run_coroutine_threadsafe(self._async_find_ui_element(target_description, img), loop)
            return future.result()
        else:
            return loop.run_until_complete(self._async_find_ui_element(target_description, img))

vision_agent = VisionAgent()
