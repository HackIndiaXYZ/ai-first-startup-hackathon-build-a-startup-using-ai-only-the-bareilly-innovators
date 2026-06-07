import threading
import subprocess
import pygame
import os
import tempfile
import time

class EdgeSpeaker:
    def __init__(self, voice="en-US-ChristopherNeural"):
        self.voice = voice
        try:
            pygame.mixer.init()
        except Exception:
            pass
        self.temp_dir = tempfile.gettempdir()

    def speak(self, text: str):
        if not text:
            return
        # Run in a separate thread to not block the caller
        threading.Thread(target=self._speak_sync, args=(text,), daemon=True).start()

    def _speak_sync(self, text):
        try:
            temp_file = os.path.join(self.temp_dir, f"edge_tts_{int(time.time()*1000)}.mp3")
            
            # Use the CLI to generate the file
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            import sys
            subprocess.run(
                [sys.executable, "-m", "edge_tts", "--voice", self.voice, "--text", text, "--write-media", temp_file],
                check=True,
                creationflags=creation_flags
            )
            
            # Wait for previous to finish if necessary
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
                
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
                
            pygame.mixer.music.unload()
            
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
        except Exception as e:
            print(f" EdgeSpeaker Error: {e}")

edge_speaker = EdgeSpeaker()
