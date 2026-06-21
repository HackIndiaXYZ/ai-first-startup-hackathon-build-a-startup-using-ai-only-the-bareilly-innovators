import speech_recognition as sr
import time

def callback(recognizer, audio):
    try:
        text = recognizer.recognize_google(audio).lower()
        print(f"Heard: {text}")
    except Exception as e:
        print("Error/Unknown:", e)

r = sr.Recognizer()
m = sr.Microphone()
with m as source:
    r.adjust_for_ambient_noise(source)
print("Listening...")
stop = r.listen_in_background(m, callback, phrase_time_limit=3)

time.sleep(10)
stop()
