from core.custom_wake_word import CustomWakeWordEngine
import time
engine = CustomWakeWordEngine()
engine.start_listening(lambda: print("Triggered"))
