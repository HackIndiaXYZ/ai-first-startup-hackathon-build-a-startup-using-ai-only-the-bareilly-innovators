"""
SIVI AI  Spotify Controller Module
Voice-controlled Spotify playback via Spotipy (Web API).
Requires: pip install spotipy
Requires: SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI in .env
"""

import os

try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    _spotipy_available = True
except ImportError:
    _spotipy_available = False


class SpotifyController:
    def __init__(self):
        self.sp = None
        if not _spotipy_available:
            print(" Spotipy not installed. Run: pip install spotipy")
            return

        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")

        if not client_id or not client_secret:
            print(" Spotify credentials not found in .env")
            return

        try:
            self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope="user-modify-playback-state user-read-playback-state user-read-currently-playing",
                cache_path=".spotify_cache",
            ))
            print(" Spotify connected.")
        except Exception as e:
            print(f" Spotify auth failed: {e}")

    def handle_command(self, text: str) -> str:
        if not self.sp:
            return "Spotify is not configured. Add SPOTIFY keys to .env."

        text = text.lower().strip()

        try:
            if "spotify play " in text:
                query = text.split("spotify play ")[-1].strip()
                return self._play_search(query)
            elif "spotify pause" in text:
                self.sp.pause_playback()
                return "Spotify paused."
            elif "spotify resume" in text or "spotify continue" in text:
                self.sp.start_playback()
                return "Spotify resumed."
            elif "spotify next" in text or "spotify skip" in text:
                self.sp.next_track()
                return "Skipped to next track."
            elif "spotify previous" in text:
                self.sp.previous_track()
                return "Playing previous track."
            elif "spotify shuffle on" in text:
                self.sp.shuffle(True)
                return "Shuffle enabled."
            elif "spotify shuffle off" in text:
                self.sp.shuffle(False)
                return "Shuffle disabled."
            elif "spotify volume" in text:
                vol = int("".join(filter(str.isdigit, text)) or "50")
                self.sp.volume(min(100, max(0, vol)))
                return f"Spotify volume set to {vol}%."
            elif "what's playing" in text or "current song" in text:
                return self._current_track()
            else:
                return "Unknown Spotify command."
        except Exception as e:
            return f"Spotify error: {e}"

    def _play_search(self, query: str) -> str:
        results = self.sp.search(q=query, limit=1, type="track")
        tracks = results.get("tracks", {}).get("items", [])
        if tracks:
            track = tracks[0]
            self.sp.start_playback(uris=[track["uri"]])
            return f"Playing '{track['name']}' by {track['artists'][0]['name']}."
        return f"Could not find '{query}' on Spotify."

    def _current_track(self) -> str:
        current = self.sp.current_playback()
        if current and current.get("item"):
            track = current["item"]
            return f"Now playing: '{track['name']}' by {track['artists'][0]['name']}."
        return "Nothing is currently playing."


spotify_controller = SpotifyController()
