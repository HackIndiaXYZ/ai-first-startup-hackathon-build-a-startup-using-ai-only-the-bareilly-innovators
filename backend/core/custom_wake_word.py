import os
import time
import pyaudio
import numpy as np

try:
    from openwakeword.model import Model
    _oww_available = True
except ImportError:
    _oww_available = False
    print(" openwakeword not installed. Run: pip install openwakeword")

class ClapDetector:
    """
    Detects double claps as a wake word fallback/alternative.
    """
    def __init__(self, threshold=12000, max_delay=1.5, min_delay=0.15):
        self.threshold = float(os.getenv("CLAP_THRESHOLD", threshold))
        self.max_delay = max_delay
        self.min_delay = min_delay
        self.claps = 0
        self.last_clap_time = 0

    def process(self, audio_data: np.ndarray) -> bool:
        # Calculate max amplitude for the chunk
        max_amp = np.max(np.abs(audio_data))
        current_time = time.time()
        
        if max_amp > self.threshold:
            time_since_last = current_time - self.last_clap_time
            
            # Prevent single long loud noise from triggering multiple claps
            if time_since_last > self.min_delay:
                if time_since_last <= self.max_delay:
                    self.claps += 1
                else:
                    # Reset sequence if too much time passed
                    self.claps = 1
                
                self.last_clap_time = current_time
                print(f" [Audio Peak] Amplitude: {max_amp} | Claps: {self.claps}")
                
                if self.claps >= 2:  # Double clap detected
                    self.claps = 0
                    return True
        return False

class CustomWakeWordEngine:
    def __init__(self, model_path=None):
        self.oww_model = None
        self.use_oww = False

        if _oww_available:
            env_path = os.getenv("WAKE_WORD_MODEL_PATH", "")
            self.model_path = model_path or (env_path if env_path else "hey_sivi")
            
            if self.model_path and self.model_path.endswith(".onnx") and os.path.exists(self.model_path):
                try:
                    print(f" Loading OpenWakeWord model: {self.model_path}")
                    self.oww_model = Model(
                        wakeword_models=[self.model_path],
                        inference_framework="onnx"
                    )
                    self.use_oww = True
                except Exception as e:
                    print(f" Failed to load OpenWakeWord model: {e}")
            else:
                print(" No valid ONNX model found for OpenWakeWord.")

        # Initialize Clap Detector
        self.clap_detector = ClapDetector()
        print(" Double-Clap Wake System initialized (Always Active).")

        # PyAudio Setup
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.CHUNK = 1280
        self._audio = pyaudio.PyAudio()
        self.mic_stream = None
        self._running = False

    def start_listening(self, callback):
        self._running = True
        
        print(" Starting microphone stream for Wake Word / Clap detection...")
        try:
            self.mic_stream = self._audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK
            )
        except Exception as e:
            print(f" Failed to open microphone: {e}")
            return

        threshold = float(os.getenv("WAKE_WORD_THRESHOLD", "0.5"))
        if self.use_oww:
            print(f" Voice wake word threshold: {threshold}")
        print(f" Clap detection threshold: {self.clap_detector.threshold}")

        try:
            while self._running:
                # Read audio chunk; suppress overflow errors
                raw = self.mic_stream.read(self.CHUNK, exception_on_overflow=False)
                audio_data = np.frombuffer(raw, dtype=np.int16)

                triggered = False

                # 1. Check Clap Detection
                if self.clap_detector.process(audio_data):
                    print(" =========================================")
                    print("  👏 DOUBLE CLAP DETECTED! Waking up...  ")
                    print(" =========================================")
                    triggered = True

                # 2. Check OpenWakeWord if available
                if not triggered and self.use_oww and self.oww_model:
                    prediction = self.oww_model.predict(audio_data)
                    for model_key, score in prediction.items():
                        if score > threshold:
                            print(f" Wake word detected! Confidence: {score:.2f}")
                            self.oww_model.reset()
                            triggered = True
                            break

                if triggered:
                    callback()
                    # Sleep briefly to avoid immediate re-triggers if noise continues
                    time.sleep(1.5)
                    # Reset buffers
                    try:
                        available = self.mic_stream.get_read_available()
                        if available > 0:
                            self.mic_stream.read(available, exception_on_overflow=False)
                    except Exception:
                        pass

        except KeyboardInterrupt:
            print(" Wake word detection stopped by user.")
        except Exception as e:
            print(f" Wake word engine error: {e}")
        finally:
            self.stop()

    def stop(self):
        self._running = False
        if self.mic_stream:
            try:
                self.mic_stream.stop_stream()
                self.mic_stream.close()
            except Exception:
                pass
            self.mic_stream = None
        try:
            self._audio.terminate()
        except Exception:
            pass
