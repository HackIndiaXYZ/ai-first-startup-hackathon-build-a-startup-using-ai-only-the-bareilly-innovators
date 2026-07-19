"""
SIVI 3.0 — Camera Vision Module
Uses webcam + Gemini Vision for real emotion/wellness analysis.
Falls back gracefully if camera is unavailable.
"""

import logging
import threading

logger = logging.getLogger("sivi.camera_vision")

try:
    import cv2
    _cv2_available = True
except ImportError:
    _cv2_available = False

from core.genai_runner import run_with_key_pool


class CameraVision:
    def __init__(self):
        self._lock = threading.Lock()

    def _capture_frame(self):
        """Capture a single frame from the default webcam."""
        if not _cv2_available:
            return None
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return None
            ret, frame = cap.read()
            cap.release()
            if ret:
                # Convert BGR to RGB for PIL
                from PIL import Image
                import numpy as np
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                return Image.fromarray(rgb)
            return None
        except Exception as e:
            logger.debug(f"[CameraVision] Failed to capture frame: {e}")
            return None

    def analyze_emotion(self) -> str:
        """Analyze the user's facial expression/emotion via webcam + Gemini."""
        with self._lock:
            img = self._capture_frame()
            if img is None:
                return "Camera unavailable — cannot analyze emotion."

            try:
                def make_call(client):
                    return client.models.generate_content(
                        model='gemini-2.0-flash',
                        contents=[
                            "Look at this webcam image. In ONE short sentence, describe the person's "
                            "apparent mood or emotion (e.g., 'looks focused', 'seems tired', 'appears happy'). "
                            "If no face is visible, say 'No face detected.'",
                            img
                        ]
                    )

                response = run_with_key_pool(make_call)
                if response is None:
                    return "Emotion analysis unavailable (API quota)."
                return response.text.strip()
            except Exception as e:
                logger.debug(f"[CameraVision] Emotion analysis failed: {e}")
                return "Emotion analysis failed."

    def analyze_wellness(self) -> str:
        """Analyze posture/wellness via webcam + Gemini."""
        with self._lock:
            img = self._capture_frame()
            if img is None:
                return "Camera unavailable — cannot analyze wellness."

            try:
                def make_call(client):
                    return client.models.generate_content(
                        model='gemini-2.0-flash',
                        contents=[
                            "Look at this webcam image. In ONE short sentence, assess the person's "
                            "physical state: posture, signs of fatigue/stress, or if they look healthy. "
                            "Focus on observable cues only. If no person is visible, say 'No person detected.'",
                            img
                        ]
                    )

                response = run_with_key_pool(make_call)
                if response is None:
                    return "Wellness check unavailable (API quota)."
                return response.text.strip()
            except Exception as e:
                logger.debug(f"[CameraVision] Wellness analysis failed: {e}")
                return "Wellness analysis failed."


camera_vision = CameraVision()
