"""
TITAN — Wake Word Detection
Listens for wake word, then sends voice to the Gemini Live bridge server.
Uses HTTP POST to /voice/send-text to integrate with the running bridge server.
"""

import os
import sys
import threading
import requests
import win32gui

# Fix: Ensure core/ is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from custom_wake_word import CustomWakeWordEngine
from dotenv import load_dotenv
import speech_recognition as sr

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

BRIDGE_URL = os.getenv("BRIDGE_URL", "http://localhost:8000")


class WakeWordListener:
    """
    Standalone wake word listener that integrates with the bridge server.

    Flow:
      1. OpenWakeWord detects wake word → fires callback
      2. Records user command via Google STT (short burst)
      3. POSTs the text to /voice/send-text → Gemini Live responds via audio
      4. Returns to listening state

    If bridge server is offline, falls back to local pyttsx3 TTS for acknowledgement.
    """

    def __init__(self):
        self.wake_engine = CustomWakeWordEngine()
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self._cooldown = False

    def _bridge_connected(self) -> bool:
        try:
            r = requests.get(f"{BRIDGE_URL}/health", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def _speak_local(self, text: str):
        """Fallback TTS using pyttsx3 when bridge is offline."""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            if voices and len(voices) > 1:
                engine.setProperty('voice', voices[1].id)
            engine.setProperty('rate', 175)
            clean = text.encode('ascii', 'ignore').decode('ascii')
            print(f" [Wake Word TTS] {clean}")
            engine.say(clean)
            engine.runAndWait()
        except Exception as e:
            print(f" Local TTS failed: {e}")

    def _send_to_bridge(self, text: str) -> bool:
        """Send recognized text to the Gemini Live bridge server."""
        try:
            r = requests.post(
                f"{BRIDGE_URL}/voice/send-text",
                json={"text": text},
                timeout=5
            )
            return r.status_code == 200
        except Exception as e:
            print(f" Bridge POST failed: {e}")
            return False

    def on_wake_word_detected(self):
        """Called when wake word fires. Prevents re-trigger via cooldown."""
        if self._cooldown:
            return
        self._cooldown = True

        def _handle_wake():
            print("\n Wake word/Clap detected!")

            # 1. Provide an instant, polite local greeting based on time of day
            from datetime import datetime
            hour = datetime.now().hour
            if hour < 12:
                wish = "Good morning, Sir."
            elif hour < 18:
                wish = "Good afternoon, Sir."
            else:
                wish = "Good evening, Sir."
            
            greeting = f"{wish} I am listening."

            # Check if bridge server is running
            if self._bridge_connected():
                # Provide instant local feedback so the user knows to speak
                self._speak_local(greeting)

                # Get the currently active window to give Sivi context
                context = "The user has been greeted locally. Just listen carefully to their command."
                try:
                    hwnd = win32gui.GetForegroundWindow()
                    if hwnd:
                        window_title = win32gui.GetWindowText(hwnd).strip()
                        if window_title:
                            context = f"The user is looking at: {window_title}. The local system already said '{greeting}'. Just listen to their command and execute it."
                except Exception:
                    pass

                # Bridge is online — send a nudge so Gemini starts listening
                self._send_to_bridge(f"[WAKE_WORD_ACTIVATED: User just woke you up. {context}]")
                print(" Bridge is online. Waiting for user to speak into Gemini Live mic.")
            else:
                # Bridge offline — fall back to local command handling
                self._speak_local(greeting)
                self._listen_local_command()

            # Reset cooldown after 3 seconds
            threading.Timer(3.0, self._reset_cooldown).start()

        # Offload the blocking requests and STT to a background thread 
        # so the microphone stream loop doesn't get stuck!
        threading.Thread(target=_handle_wake, daemon=True).start()

    def _reset_cooldown(self):
        self._cooldown = False

    def _listen_local_command(self):
        """Local STT + command execution fallback (when bridge is offline)."""
        try:
            from jarvis_controller import controller
        except ImportError:
            print(" jarvis_controller not available for local fallback.")
            return

        with sr.Microphone() as source:
            print(" Adjusting for ambient noise... Listening for local command...")
            # Adjust longer for ambient noise to catch speech properly
            self.recognizer.adjust_for_ambient_noise(source, duration=1.0)
            try:
                # Increased timeout to 8s and phrase limit to 15s to hear them properly
                audio = self.recognizer.listen(source, timeout=8, phrase_time_limit=15)
                print(" Processing audio...")
                command = self.recognizer.recognize_google(audio)
                print(f" You said: {command}")
                response = controller.process_command(command)
                if response:
                    self._speak_local(response)
            except sr.WaitTimeoutError:
                self._speak_local("I didn't hear anything, Sir.")
            except sr.UnknownValueError:
                self._speak_local("Sorry, I couldn't understand that clearly.")
            except sr.RequestError as e:
                print(f" Google STT error: {e}")
                self._speak_local("Speech service unavailable, please check internet.")
            except Exception as e:
                print(f" Speech recognition error: {e}")

    def run(self):
        bridge_status = "online" if self._bridge_connected() else "OFFLINE (local fallback active)"
        print(f"\n TITAN Wake Word Listener starting...")
        print(f"   Bridge server: {BRIDGE_URL} [{bridge_status}]")
        print(f"   Listening for wake word / claps...\n")

        self.wake_engine.start_listening(self.on_wake_word_detected)


if __name__ == "__main__":
    listener = WakeWordListener()
    listener.run()
