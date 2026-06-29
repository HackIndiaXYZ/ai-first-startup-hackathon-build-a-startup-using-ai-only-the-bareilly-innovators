"""
SIVI AI — Vision Agent
Leverages Gemini's spatial reasoning to find the X, Y coordinates of UI elements on the screen.
"""

import os
import re
import json
import pyautogui
from PIL import ImageGrab, Image

try:
    from google import genai
except ImportError:
    genai = None

def _get_api_key():
    key = os.getenv("GEMINI_API_KEY")
    if key: return key
    try:
        settings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sivi_settings.json")
        with open(settings_path, "r") as f:
            return json.load(f).get("api_key")
    except Exception:
        return None

class VisionAgent:
    def __init__(self):
        self.model_name = "gemini-flash-latest"
        
    def _get_client(self):
        if not genai: return None
        key = _get_api_key()
        return genai.Client(api_key=key) if key else None

    def find_ui_element(self, target_description: str, img: Image.Image = None) -> tuple[int, int]:
        """
        Uses Gemini to find the bounding box of a UI element on the screen.
        Returns the (x, y) logical center coordinates of the element, or None if not found.
        """
        client = self._get_client()
        if not client:
            print(" Vision Agent offline. No API key.")
            return None

        if img is None:
            try:
                img = ImageGrab.grab()
            except Exception as e:
                print("=========================================================")
                print(" ERROR: VISION AGENT FAILED TO CAPTURE SCREEN")
                print(" macOS is blocking screen capture!")
                print(" Please go to System Settings -> Privacy & Security -> Screen Recording")
                print(" and grant permissions to your Terminal / iTerm / Python.")
                print("=========================================================")
                return None

        prompt = f"""Find the bounding box of this exact UI element: "{target_description}"
Respond ONLY with a JSON array of 4 integers scaled to 1000: [ymin, xmin, ymax, xmax].
Do not output any markdown. Just the array.
If the element is absolutely nowhere on the screen, respond exactly with: None"""

        try:
            print(f" Vision Agent analyzing screen for: {target_description}...")
            response = client.models.generate_content(
                model=self.model_name,
                contents=[prompt, img]
            )
            text = response.text.strip()
            
            if "None" in text:
                print(f" Vision Agent could not find: {target_description}")
                return None
                
            # Extract [ymin, xmin, ymax, xmax]
            match = re.search(r'\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]', text)
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

vision_agent = VisionAgent()
