"""Voice activity detection.

SimpleEnergyVAD: dependency-free RMS-energy-threshold VAD. Works everywhere
(including this browser workspace) on raw 16-bit PCM frames — good enough
for push-to-talk trimming; not as robust as a trained VAD model.

WebRtcVAD: wraps the industry-standard WebRTC VAD (via `webrtcvad-wheels`)
for higher-quality speech/silence detection. LOCAL WINDOWS TEST NEEDED for
real microphone streams, though the library itself is pure C-extension and
could run here if installed — kept out of base requirements to keep the
browser workspace install light.
"""
from __future__ import annotations

import array
import math


class VoiceActivityDetector:
    def is_speech(self, frame: bytes, samplerate: int = 16000) -> bool:
        raise NotImplementedError


class SimpleEnergyVAD(VoiceActivityDetector):
    """RMS energy threshold over 16-bit signed PCM mono samples.

    Implemented without the deprecated/removed stdlib `audioop` module
    (gone in Python 3.13+) so this keeps working across Python versions.
    """

    def __init__(self, threshold: int = 500):
        self.threshold = threshold

    def is_speech(self, frame: bytes, samplerate: int = 16000) -> bool:
        if not frame or len(frame) < 2:
            return False
        samples = array.array("h")
        usable_len = len(frame) - (len(frame) % 2)
        samples.frombytes(frame[:usable_len])
        if not samples:
            return False
        mean_sq = sum(s * s for s in samples) / len(samples)
        rms = math.sqrt(mean_sq)
        return rms >= self.threshold


class WebRtcVAD(VoiceActivityDetector):
    def __init__(self, aggressiveness: int = 2):
        try:
            import webrtcvad  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "webrtcvad-wheels is required for WebRtcVAD. "
                "Run: pip install -r requirements/windows.txt"
            ) from exc
        self._vad = webrtcvad.Vad(aggressiveness)

    def is_speech(self, frame: bytes, samplerate: int = 16000) -> bool:
        return self._vad.is_speech(frame, samplerate)
