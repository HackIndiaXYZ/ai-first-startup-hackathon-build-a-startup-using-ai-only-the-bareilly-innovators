import os
import pyaudio
import numpy as np

try:
    from openwakeword.model import Model
    _oww_available = True
except ImportError:
    _oww_available = False
    print(" openwakeword not installed. Run: pip install openwakeword")


class CustomWakeWordEngine:
    def __init__(self, model_path=None):
        if not _oww_available:
            raise RuntimeError("openwakeword is not installed.")

        # Use model_path param > env var > default pre-trained model
        env_path = os.getenv("WAKE_WORD_MODEL_PATH", "")
        self.model_path = model_path or (env_path if env_path else "hey_jarvis")

        print(f" Loading OpenWakeWord model: {self.model_path}")

        try:
            # Initialize OpenWakeWord with the specific model
            self.oww_model = Model(
                wakeword_models=[self.model_path],
                inference_framework="onnx"
            )
        except Exception as e:
            print(f" Failed to load model '{self.model_path}': {e}")
            print(" Falling back to 'hey_jarvis' default model...")
            self.model_path = "hey_jarvis"
            self.oww_model = Model(
                wakeword_models=[self.model_path],
                inference_framework="onnx"
            )

        # PyAudio Setup
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.CHUNK = 1280
        self._audio = pyaudio.PyAudio()
        self.mic_stream = None
        self._running = False

    def start_listening(self, callback):
        print(" Starting microphone stream for Wake Word detection...")
        self._running = True
        self.mic_stream = self._audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )

        threshold = float(os.getenv("WAKE_WORD_THRESHOLD", "0.5"))
        print(f" Wake word threshold: {threshold}")

        try:
            while self._running:
                # Read audio chunk; suppress overflow errors
                raw = self.mic_stream.read(self.CHUNK, exception_on_overflow=False)
                audio_data = np.frombuffer(raw, dtype=np.int16)

                # Feed to OpenWakeWord model
                prediction = self.oww_model.predict(audio_data)

                # The prediction returns a dict of model keys and confidence scores
                for model_key, score in prediction.items():
                    if score > threshold:
                        print(f" Wake word detected! Confidence: {score:.2f}")
                        # Reset model state before callback to prevent re-trigger
                        self.oww_model.reset()
                        callback()
                        break  # Don't fire multiple callbacks per chunk

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
