"""
Sivi — Audio Engine (PC Edition)
Uses sounddevice for native PCM audio capture and playback.

MIC INPUT:   16000 Hz, Mono, PCM 16-bit -> send to WebSocket
SPEAKER OUT: 24000 Hz, Mono, PCM 16-bit <- receive from WebSocket
CHUNK SIZE:  1024 bytes
"""

import queue
import threading
import logging
import time
from typing import Callable, Optional

import numpy as np

logger = logging.getLogger("sivi.audio_engine")

# Try to import sounddevice (preferred) or fall back to pyaudio
try:
    import sounddevice as sd
    AUDIO_BACKEND = "sounddevice"
    logger.info("Using sounddevice backend")
except ImportError:
    sd = None
    AUDIO_BACKEND = None
    logger.warning("sounddevice not available")

try:
    import pyaudio
    if AUDIO_BACKEND is None:
        AUDIO_BACKEND = "pyaudio"
        logger.info("Using pyaudio backend")
except ImportError:
    pyaudio = None

# ── Constants ─────────────────────────────────────────────────────

MIC_SAMPLE_RATE = 16000
SPEAKER_SAMPLE_RATE = 24000
CHANNELS = 1
CHUNK_SIZE = 4096
DTYPE = np.int16

# How long silence must persist before we consider speaking done (seconds)
SPEAKING_SILENCE_THRESHOLD = 0.2


class AudioEngine:
    """
    Handles mic recording and speaker playback with PCM audio.
    Provides amplitude (RMS) for waveform visualization.
    """

    def __init__(self):
        self._recording = False
        self._playing = False
        self._muted = False
        self._speaking = False  # True when Sivi is outputting audio

        # Playback queue for received audio chunks
        self._playback_queue: queue.Queue[bytes] = queue.Queue()

        # Audio streams
        self._mic_stream = None
        self._speaker_stream = None
        self._pyaudio_instance = None

        # Threading
        self._mic_thread: Optional[threading.Thread] = None
        self._speaker_thread: Optional[threading.Thread] = None

        # ── Callbacks ─────────────────────────────────────────────
        self.on_audio_chunk: Optional[Callable[[bytes], None]] = None
        self.on_amplitude_changed: Optional[Callable[[float], None]] = None
        self.on_speaking_started: Optional[Callable] = None
        self.on_speaking_stopped: Optional[Callable] = None

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def is_muted(self) -> bool:
        return self._muted

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    def set_muted(self, muted: bool):
        """Toggle mic mute."""
        self._muted = muted
        logger.info(f"Mic {'muted' if muted else 'unmuted'}")

    # ── Start Recording (Mic) ─────────────────────────────────────

    def start_recording(self):
        """Start capturing mic audio in a background thread."""
        if self._recording:
            return

        self._recording = True

        if AUDIO_BACKEND == "sounddevice":
            self._mic_thread = threading.Thread(target=self._mic_loop_sd, daemon=True)
        elif AUDIO_BACKEND == "pyaudio":
            self._mic_thread = threading.Thread(target=self._mic_loop_pyaudio, daemon=True)
        else:
            logger.error("No audio backend available!")
            self._recording = False
            return

        self._mic_thread.start()
        logger.info("Mic recording started (16kHz PCM)")

    def _mic_loop_sd(self):
        """Mic capture loop using sounddevice."""
        try:
            with sd.InputStream(
                samplerate=MIC_SAMPLE_RATE,
                channels=CHANNELS,
                dtype='int16',
                blocksize=CHUNK_SIZE // 2,  # samples, not bytes
            ) as stream:
                self._mic_stream = stream
                while self._recording:
                    data, overflowed = stream.read(CHUNK_SIZE // 2)
                    if overflowed:
                        logger.debug("Mic buffer overflow")

                    pcm_bytes = data.tobytes()

                    # Calculate RMS amplitude
                    rms = self._calculate_rms(data)
                    if self.on_amplitude_changed:
                        self.on_amplitude_changed(rms)

                    # Only send mic data to callback if not muted
                    # Note: Echo suppression is handled entirely in bridge_server.on_mic_chunk
                    if not self._muted:
                        if self.on_audio_chunk:
                            self.on_audio_chunk(pcm_bytes)
        except Exception as e:
            logger.error(f"Mic error (sounddevice): {e}")
        finally:
            self._recording = False
            self._mic_stream = None

    def _mic_loop_pyaudio(self):
        """Mic capture loop using pyaudio."""
        try:
            self._pyaudio_instance = pyaudio.PyAudio()
            stream = self._pyaudio_instance.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=MIC_SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE // 2,
            )
            self._mic_stream = stream

            while self._recording:
                pcm_bytes = stream.read(CHUNK_SIZE // 2, exception_on_overflow=False)
                data = np.frombuffer(pcm_bytes, dtype=np.int16)

                # Calculate RMS
                rms = self._calculate_rms(data)
                if self.on_amplitude_changed:
                    self.on_amplitude_changed(rms)

                if not self._muted:
                    if self.on_audio_chunk:
                        self.on_audio_chunk(pcm_bytes)

            stream.stop_stream()
            stream.close()
        except Exception as e:
            logger.error(f"Mic error (pyaudio): {e}")
        finally:
            self._recording = False
            self._mic_stream = None
            if self._pyaudio_instance:
                try:
                    self._pyaudio_instance.terminate()
                except Exception:
                    pass
                self._pyaudio_instance = None

    # ── Start Playback (Speaker) ──────────────────────────────────

    def start_playback(self):
        """Start speaker playback in a background thread."""
        if self._playing:
            return

        self._playing = True

        if AUDIO_BACKEND == "sounddevice":
            self._speaker_thread = threading.Thread(target=self._speaker_loop_sd, daemon=True)
        elif AUDIO_BACKEND == "pyaudio":
            self._speaker_thread = threading.Thread(target=self._speaker_loop_pyaudio, daemon=True)
        else:
            logger.error("No audio backend available!")
            self._playing = False
            return

        self._speaker_thread.start()
        logger.info("Speaker playback started (24kHz PCM)")

    def _speaker_loop_sd(self):
        """Speaker playback loop using sounddevice."""
        last_audio_time = 0.0
        try:
            with sd.OutputStream(
                samplerate=SPEAKER_SAMPLE_RATE,
                channels=CHANNELS,
                dtype='int16',
                blocksize=CHUNK_SIZE // 2,
            ) as stream:
                self._speaker_stream = stream
                while self._playing:
                    try:
                        chunk = self._playback_queue.get(timeout=0.05)
                        if chunk:
                            data = np.frombuffer(chunk, dtype=np.int16)
                            # Notify speaking started
                            if not self._speaking:
                                self._speaking = True
                                if self.on_speaking_started:
                                    self.on_speaking_started()
                            last_audio_time = time.time()
                            stream.write(data)
                    except queue.Empty:
                        # No audio — check if silence has lasted long enough
                        if self._speaking:
                            elapsed = time.time() - last_audio_time
                            if elapsed >= SPEAKING_SILENCE_THRESHOLD:
                                self._speaking = False
                                if self.on_speaking_stopped:
                                    self.on_speaking_stopped()
        except Exception as e:
            logger.error(f"Speaker error (sounddevice): {e}")
        finally:
            self._playing = False
            self._speaking = False
            self._speaker_stream = None

    def _speaker_loop_pyaudio(self):
        """Speaker playback loop using pyaudio."""
        last_audio_time = 0.0
        try:
            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SPEAKER_SAMPLE_RATE,
                output=True,
                frames_per_buffer=CHUNK_SIZE // 2,
            )
            self._speaker_stream = stream

            while self._playing:
                try:
                    chunk = self._playback_queue.get(timeout=0.05)
                    if chunk:
                        if not self._speaking:
                            self._speaking = True
                            if self.on_speaking_started:
                                self.on_speaking_started()
                        last_audio_time = time.time()
                        stream.write(chunk)
                except queue.Empty:
                    if self._speaking:
                        elapsed = time.time() - last_audio_time
                        if elapsed >= SPEAKING_SILENCE_THRESHOLD:
                            self._speaking = False
                            if self.on_speaking_stopped:
                                self.on_speaking_stopped()

            stream.stop_stream()
            stream.close()
            pa.terminate()
        except Exception as e:
            logger.error(f"Speaker error (pyaudio): {e}")
        finally:
            self._playing = False
            self._speaking = False
            self._speaker_stream = None

    # ── Queue Audio for Playback ──────────────────────────────────

    def queue_audio(self, pcm_bytes: bytes):
        """Add received audio chunk to playback queue."""
        self._playback_queue.put(pcm_bytes)

    def clear_playback_queue(self):
        """Clear all queued audio (interrupt Sivi)."""
        while not self._playback_queue.empty():
            try:
                self._playback_queue.get_nowait()
            except queue.Empty:
                break
        self._speaking = False
        if self.on_speaking_stopped:
            self.on_speaking_stopped()
        logger.info("Playback queue cleared (interrupted)")

    # ── RMS Calculation ───────────────────────────────────────────

    @staticmethod
    def _calculate_rms(data: np.ndarray) -> float:
        """Calculate Root Mean Square amplitude, normalized 0.0-1.0."""
        if len(data) == 0:
            return 0.0
        rms = np.sqrt(np.mean(data.astype(np.float32) ** 2))
        # Normalize to 0-1 range (16-bit audio max is 32768)
        normalized = min(rms / 8000.0, 1.0)
        return normalized

    # ── Stop / Release ────────────────────────────────────────────

    def stop_recording(self):
        """Stop mic recording."""
        self._recording = False
        logger.info("Mic recording stopped")

    def stop_playback(self):
        """Stop speaker playback."""
        self._playing = False
        self.clear_playback_queue()
        logger.info("Speaker playback stopped")

    def release(self):
        """Release all audio resources."""
        self.stop_recording()
        self.stop_playback()
        # Wait briefly for threads to finish
        if self._mic_thread and self._mic_thread.is_alive():
            self._mic_thread.join(timeout=2.0)
        if self._speaker_thread and self._speaker_thread.is_alive():
            self._speaker_thread.join(timeout=2.0)
        logger.info("Audio engine released")
