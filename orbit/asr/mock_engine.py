"""Mock ASR engine — used for tests and for exercising the full ORBIT pipeline
in the browser workspace, where no microphone or model is available.

Feed it canned transcripts up front, or use `enqueue()` to script a sequence
of "utterances" for a scripted test/demo.
"""
from __future__ import annotations

from collections import deque
from typing import Optional

from orbit.asr.base import ASREngine, AudioInput, TranscriptionResult, TranscriptSegment


class MockASREngine(ASREngine):
    name = "mock"

    def __init__(self, default_text: str = "", default_language: str = "en"):
        self.default_text = default_text
        self.default_language = default_language
        self._queue: deque[tuple[str, str]] = deque()

    def enqueue(self, text: str, language: str = "en") -> None:
        self._queue.append((text, language))

    def transcribe(self, audio: AudioInput, language: Optional[str] = None) -> TranscriptionResult:
        if self._queue:
            text, lang = self._queue.popleft()
        else:
            text, lang = self.default_text, self.default_language
        return TranscriptionResult(
            raw_text=text,
            language=language or lang,
            segments=[TranscriptSegment(text=text, start=0.0, end=max(len(text) * 0.05, 0.1), confidence=0.95)],
            confidence=0.95,
            engine=self.name,
        )
