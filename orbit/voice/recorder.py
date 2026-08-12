"""Microphone capture abstraction.

SimulatedAudioRecorder: returns pre-loaded bytes/paths — used for tests and
for exercising the pipeline in this browser workspace (no microphone here).

RealAudioRecorder: captures from an actual microphone via `sounddevice`.
LOCAL WINDOWS TEST NEEDED.
"""
from __future__ import annotations

from pathlib import Path


class AudioRecorder:
    def start(self) -> None:
        raise NotImplementedError

    def stop(self) -> bytes:
        raise NotImplementedError


class SimulatedAudioRecorder(AudioRecorder):
    def __init__(self, canned_audio: bytes = b""):
        self.canned_audio = canned_audio
        self.recording = False

    def start(self) -> None:
        self.recording = True

    def stop(self) -> bytes:
        self.recording = False
        return self.canned_audio

    def set_canned_audio(self, audio: bytes) -> None:
        self.canned_audio = audio


class RealAudioRecorder(AudioRecorder):
    """Captures real microphone audio via sounddevice. LOCAL WINDOWS TEST
    NEEDED — no audio device is available in this browser workspace.
    """

    def __init__(self, samplerate: int = 16000, channels: int = 1):
        try:
            import sounddevice as sd  # type: ignore
            import numpy as np  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "sounddevice/numpy are required for microphone capture. "
                "Run: pip install -r requirements/windows.txt"
            ) from exc
        self._sd = sd
        self._np = np
        self.samplerate = samplerate
        self.channels = channels
        self._frames: list = []
        self._stream = None

    def _callback(self, indata, frames, time_info, status) -> None:
        self._frames.append(indata.copy())

    def start(self) -> None:
        self._frames = []
        # int16 explicitly -- `save_wav` writes 16-bit PCM (sampwidth=2).
        # sounddevice defaults to float32, which would silently produce a
        # corrupt/garbled WAV file if written out with a 16-bit header.
        self._stream = self._sd.InputStream(
            samplerate=self.samplerate, channels=self.channels, dtype="int16", callback=self._callback
        )
        self._stream.start()

    def stop(self) -> bytes:
        if self._stream:
            self._stream.stop()
            self._stream.close()
        if not self._frames:
            return b""
        audio = self._np.concatenate(self._frames, axis=0)
        return audio.tobytes()

    def save_wav(self, path: str | Path, audio_bytes: bytes) -> Path:
        import wave

        p = Path(path)
        with wave.open(str(p), "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.samplerate)
            wf.writeframes(audio_bytes)
        return p
