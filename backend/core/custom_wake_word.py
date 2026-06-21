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
    def __init__(self, threshold=4000, max_delay=2.0, min_delay=0.1):
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
        self.use_vosk = False
        self.recognizer = None
        
        # Initialize Vosk
        try:
            from vosk import Model, KaldiRecognizer
            import json
            
            # Use the local vosk-model if it exists
            env_path = os.getenv("WAKE_WORD_MODEL_PATH", "vosk-model")
            if os.path.exists(env_path):
                print(f" Loading Vosk model: {env_path}")
                model = Model(env_path)
                self.recognizer = KaldiRecognizer(model, 16000)
                self.use_vosk = True
            else:
                print(" Vosk model not found. Falling back to clap detection.")
        except ImportError:
            print(" Vosk not installed. Run: pip install vosk")
        except Exception as e:
            print(f" Failed to load Vosk model: {e}")

        # Initialize Clap Detector fallback
        self.clap_detector = ClapDetector()
        print(" Wake Word System initialized.")

        # PyAudio Setup
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.CHUNK = 4000
        self._audio = pyaudio.PyAudio()
        self.mic_stream = None
        self._running = False

    def start_listening(self, callback):
        self._running = True
        
        print(" Starting microphone stream for Wake Word detection...")
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

        try:
            while self._running:
                raw = self.mic_stream.read(self.CHUNK, exception_on_overflow=False)
                audio_data = np.frombuffer(raw, dtype=np.int16)

                triggered = False

                # 1. Check Vosk
                if self.use_vosk and self.recognizer:
                    if self.recognizer.AcceptWaveform(raw):
                        import json
                        res = json.loads(self.recognizer.Result())
                        text = res.get("text", "").lower()
                        if text:
                            # print(f" [Vosk] Heard: {text}")
                            if "sivi" in text or "see we" in text or "cb" in text or "tv" in text or "cv" in text or "civil" in text or "siri" in text:
                                print(f" \n Wake word detected! (Heard: '{text}')")
                                triggered = True
                
                # 2. Check Clap Detection
                if not triggered and self.clap_detector.process(audio_data):
                    print(" =========================================")
                    print("  👏 DOUBLE CLAP DETECTED! Waking up...  ")
                    print(" =========================================")
                    triggered = True

                if triggered:
                    callback()
                    time.sleep(0.5)
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

