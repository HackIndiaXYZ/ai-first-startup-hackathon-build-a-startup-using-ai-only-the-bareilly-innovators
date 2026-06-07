import threading
import time
import base64
import cv2
import mss
import numpy as np
import requests
try:
    from core.edge_speaker import edge_speaker
except ImportError:
    from edge_speaker import edge_speaker

class ContinuousObserver:
    def __init__(self):
        self.running = False
        self.thread = None
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model_name = "llava"  # Most stable vision model on Ollama
        self.previous_frame = None

    def start(self):
        if self.running:
            return "Screen observer is already running."
        self.running = True
        self.thread = threading.Thread(target=self._observe_loop, daemon=True)
        self.thread.start()
        edge_speaker.speak("I am now monitoring your screen continuously.")
        return "Started continuous screen observation."

    def stop(self):
        if not self.running:
            return "Screen observer is not running."
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        edge_speaker.speak("I have stopped monitoring your screen.")
        return "Stopped continuous screen observation."

    def _observe_loop(self):
        with mss.mss() as sct:
            monitor = sct.monitors[1]  # Primary monitor
            while self.running:
                try:
                    # 1. Capture screen
                    sct_img = sct.grab(monitor)
                    # Convert to numpy array
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
                        
                        print(" [Observer] Sending frame to Ollama...")
                        response = requests.post(self.ollama_url, json=payload, timeout=120)
                        if response.status_code == 200:
                            result_text = response.json().get("response", "").strip()
                            if result_text:
                                print(f" [Observer] Ollama: {result_text}")
                                edge_speaker.speak(result_text)
                                
                    # 4. Sleep to prevent overloading system
                    # Wait 8 seconds before next capture
                    for _ in range(80):
                        if not self.running:
                            break
                        time.sleep(0.1)

                except requests.exceptions.ConnectionError:
                    print(" [Observer Error] Could not connect to Ollama. Is it running?")
                    time.sleep(5)
                except Exception as e:
                    print(f" [Observer Error] {e}")
                    time.sleep(5)

continuous_observer = ContinuousObserver()
