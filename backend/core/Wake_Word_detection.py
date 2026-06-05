import os
import sys

# Fix: Ensure core/ is on the path regardless of how this file is launched
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from custom_wake_word import CustomWakeWordEngine
from jarvis_controller import controller
import speech_recognition as sr
import pyttsx3
from personality import get_greeting
from dotenv import load_dotenv

# Load .env from the backend/ directory
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


class WakeWordListener:
    def __init__(self):
        self.wake_engine = CustomWakeWordEngine()
        self.recognizer = sr.Recognizer()

        # TTS Engine Setup
        self.engine = pyttsx3.init()
        voices = self.engine.getProperty('voices')
        # Prefer a female voice if available (index 1), else default
        if voices:
            if len(voices) > 1:
                self.engine.setProperty('voice', voices[1].id)
            else:
                self.engine.setProperty('voice', voices[0].id)
        self.engine.setProperty('rate', 175)   # Slightly slower for clarity
        self.engine.setProperty('volume', 1.0)

    def speak(self, text):
        # Strip emojis/non-ASCII so pyttsx3 doesn't choke
        clean = text.encode('ascii', 'ignore').decode('ascii')
        print(f" Assistant: {text}")
        self.engine.say(clean)
        self.engine.runAndWait()

    def on_wake_word_detected(self):
        self.speak("Yes sir?")
        self.listen_for_command()

    def listen_for_command(self):
        with sr.Microphone() as source:
            print(" Listening for command...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                command = self.recognizer.recognize_google(audio)
                print(f" You said: {command}")

                # Forward to Jarvis Controller
                response = controller.process_command(command)
                if response:
                    self.speak(response)

            except sr.WaitTimeoutError:
                print(" Command timeout.")
                self.speak("I didn't catch that. Please try again.")
            except sr.UnknownValueError:
                print(" Could not understand audio.")
                self.speak("Sorry, I couldn't understand that.")
            except sr.RequestError as e:
                print(f" Google STT error: {e}")
                self.speak("Speech service unavailable. Check your internet.")
            except Exception as e:
                print(f" Speech recognition error: {e}")

    def run(self):
        user_name = os.getenv("USER_NAME", "Boss")
        mode = os.getenv("AI_MODE", "gf")
        greeting = get_greeting(user_name, mode)
        self.speak(greeting)

        print(" TITAN Wake Word listener starting...")
        # Starts the continuous openwakeword listener block
        self.wake_engine.start_listening(self.on_wake_word_detected)


if __name__ == "__main__":
    listener = WakeWordListener()
    listener.run()
