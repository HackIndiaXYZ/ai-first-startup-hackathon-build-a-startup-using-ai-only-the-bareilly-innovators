import threading
import time
import base64
import requests
import numpy as np

try:
    import cv2
    _cv2_available = True
except ImportError:
    cv2 = None
    _cv2_available = False

try:
    import mss as mss_lib
    _mss_available = True
except ImportError:
    mss_lib = None
    _mss_available = False

import logging
logger = logging.getLogger("sivi.continuous_observer")

# Bridge callback — set by bridge_server after voice session starts
_bridge_speak_callback = None

def set_bridge_callback(callback):
    """Set the callback used to send observations through Gemini Live (Fix #17)."""
    global _bridge_speak_callback
    _bridge_speak_callback = callback


class ContinuousObserver:
    def __init__(self):
        self.running = False
        self.thread = None
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model_name = "llava"  # Most stable vision model on Ollama
        self.previous_frame = None

    def _speak(self, text: str):
        """
        Fix #17: Send through Gemini Live instead of edge_speaker,
        so observations appear in the chat and use Sivi's real voice.
        Falls back to a log if bridge is not connected.
        """
        if _bridge_speak_callback:
            try:
                import asyncio
                import concurrent.futures
                # Schedule on main event loop — bridge_callback is async
                from core.sensory_orchestrator import sensory_orchestrator
                # Re-use the bridge_callback pattern from sensory_orchestrator
                if sensory_orchestrator._bridge_callback:
                    # Post to bridge; it handles asyncio threading
                    from bridge_server import _main_loop
                    if _main_loop and _main_loop.is_running():
                        asyncio.run_coroutine_threadsafe(
                            sensory_orchestrator._bridge_callback(
                                f"[SYSTEM_EVENT: Continuous Observer detected: {text}. Briefly mention this to Boss if relevant.]"
                            ),
                            _main_loop
                        )
                    return
            except Exception as e:
                logger.debug(f"Could not route via bridge: {e}")
        logger.info(f"[Observer] {text}")

    def start(self):
        if not _cv2_available or not _mss_available:
            return "Continuous Observer requires 'opencv-python' and 'mss'. Install them and restart."
        if self.running:
            return "Screen observer is already running."
        self.running = True
        self.thread = threading.Thread(target=self._observe_loop, daemon=True)
        self.thread.start()
        self._speak("I am now monitoring your screen continuously.")
        return "Started continuous screen observation."

    def stop(self):
        if not self.running:
            return "Screen observer is not running."
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        self._speak("I have stopped monitoring your screen.")
        return "Stopped continuous screen observation."

    def _observe_loop(self):
        with mss_lib.mss() as sct:
            monitor = sct.monitors[1]  # Primary monitor
            while self.running:
                try:
                    # 1. Capture screen
                    sct_img = sct.grab(monitor)
                    frame = np.array(sct_img)

                    # 2. Downscale and convert to grayscale for diffing
                    small_frame = cv2.resize(frame, (640, 360))
                    gray_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGRA2GRAY)

                    # 3. Check for motion/change
                    should_analyze = False
                    if self.previous_frame is None:
                        should_analyze = True
                    else:
                        diff = cv2.absdiff(self.previous_frame, gray_frame)
                        mean_diff = np.mean(diff)
                        if mean_diff > 3.0:
                            should_analyze = True

                    self.previous_frame = gray_frame

                    if should_analyze:
                        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGRA2RGB)
                        _, buffer = cv2.imencode('.jpg', rgb_frame)
                        img_str = base64.b64encode(buffer).decode('utf-8')

                        prompt = "You are continuously watching my screen. Describe any significant new activities, context, or visual elements. Be very brief (1 or 2 sentences max)."

                        payload = {
                            "model": self.model_name,
                            "prompt": prompt,
                            "images": [img_str],
                            "stream": False
                        }

                        response = requests.post(self.ollama_url, json=payload, timeout=120)
                        if response.status_code == 200:
                            result_text = response.json().get("response", "").strip()
                            if result_text:
                                self._speak(result_text)

                    # 4. Sleep to prevent overloading system — 8 seconds between captures
                    for _ in range(80):
                        if not self.running:
                            break
                        time.sleep(0.1)

                except requests.exceptions.ConnectionError:
                    logger.warning("[Observer] Could not connect to Ollama. Is it running?")
                    time.sleep(5)
                except Exception as e:
                    logger.error(f"[Observer] Error: {e}")
                    time.sleep(5)


continuous_observer = ContinuousObserver()
