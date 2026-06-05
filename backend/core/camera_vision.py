import cv2
import os
from PIL import Image

try:
    from google import genai
    _genai_available = True
except ImportError:
    genai = None
    _genai_available = False
    print(" google.genai not installed. Vision will not work.")


import json

def _get_api_key():
    key = os.getenv("GEMINI_API_KEY")
    if key: return key
    try:
        settings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sivi_settings.json")
        with open(settings_path, "r") as f:
            return json.load(f).get("api_key")
    except Exception:
        return None

class CameraVision:
    def __init__(self):
        self.model_name = 'gemini-2.5-flash'

    def _get_client(self):
        if not _genai_available: return None
        key = _get_api_key()
        return genai.Client(api_key=key) if key else None

    def capture_image(self, save_path="snapshot.jpg"):
        print(" Capturing image from webcam...")
        # Use CAP_DSHOW to prevent hanging if the browser Mediapipe iframe has locked the camera
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

        if not cap.isOpened():
            # Fallback to default if DSHOW is unsupported
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return None, "Error: Could not open webcam. It might be locked by your browser's particle system."

        ret, frame = cap.read()
        cap.release()

        if ret:
            # Convert color format and save using PIL for Gemini compatibility
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            img.save(save_path)
            return img, "Image captured successfully."
        else:
            return None, "Error: Failed to read frame from webcam."

    def describe_scene(self) -> str:
        client = self._get_client()
        if not client:
            return "My AI vision is offline. Please check your Gemini API key."

        img, status = self.capture_image()
        if not img:
            return status

        print(" Analyzing image with Gemini...")
        prompt = "Describe what you see in this image in one short sentence as if you are Sivi, an AI assistant."

        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=[prompt, img]
            )
            return response.text.strip()
        except Exception as e:
            return f"Failed to analyze image: {e}"

    def analyze_emotion(self) -> str:
        """Analyzes the user's facial expressions and body language to detect mood and suggest actions."""
        client = self._get_client()
        if not client:
            return "My AI vision is offline. I cannot see you right now."

        img, status = self.capture_image()
        if not img:
            return status

        print(" Analyzing emotion and mood...")
        prompt = (
            "You are Sivi, an empathetic AI girlfriend/assistant. Look at the person in this image. "
            "1. Identify their current emotion/mood based on facial expressions and body language. "
            "2. State what they seem to be feeling. "
            "3. Offer a very short, personalized suggestion or comforting word based on their mood "
            "(e.g., if they look tired, suggest they rest or offer to play calming music. If they look happy, share their joy). "
            "Keep the response to 2 short sentences max. Speak directly to them in a caring tone."
        )

        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=[prompt, img]
            )
            return response.text.strip()
        except Exception as e:
            return f"Failed to analyze emotion: {e}"

camera_vision = CameraVision()
