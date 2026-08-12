"""ASR (speech-to-text) abstraction so the underlying model is swappable.

Keeps RAW transcript (exactly what the model heard) separate from any later
vocabulary-corrected/INTERPRETED transcript — that correction happens one
layer up, in orbit.asr.vocabulary, not inside the engine itself.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, Optional, Union

AudioInput = Union[str, Path, bytes]


@dataclass
class TranscriptSegment:
    text: str
    start: float
    end: float
    confidence: float = 1.0


@dataclass
class TranscriptionResult:
    raw_text: str
    language: str
    segments: list[TranscriptSegment] = field(default_factory=list)
    confidence: float = 1.0
    engine: str = ""


class ASREngine:
    """Abstract base for all speech-to-text engines."""

    name = "base"
    supports_streaming = False

    def transcribe(self, audio: AudioInput, language: Optional[str] = None) -> TranscriptionResult:
        raise NotImplementedError

    def transcribe_stream(
        self, audio_chunks: Iterable[bytes], language: Optional[str] = None
    ) -> Iterator[TranscriptionResult]:
        """Default streaming fallback: buffer everything then transcribe once.

        Real streaming engines should override this for low-latency partial
        results.
        """
        buf = b"".join(audio_chunks)
        yield self.transcribe(buf, language=language)
