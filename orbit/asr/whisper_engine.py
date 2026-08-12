"""faster-whisper backed ASR engine — the real local/offline speech engine.

Requires `requirements/windows.txt` (or at minimum `faster-whisper` +
`numpy`) to be installed, and a model to be downloaded via the Model
Manager (orbit.models.manager). Not installed/tested in the browser
workspace — this is exercised only after local install.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from orbit.asr.base import ASREngine, AudioInput, TranscriptionResult, TranscriptSegment

# Whisper's own language codes for the languages ORBIT explicitly targets.
SUPPORTED_LANGUAGES = {"en": "english", "hi": "hindi"}


class FasterWhisperEngine(ASREngine):
    name = "faster-whisper"

    def __init__(
        self,
        model_size: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
        download_root: Optional[Union[str, Path]] = None,
    ):
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except ImportError as exc:  # pragma: no cover - only reachable without the optional dep
            raise RuntimeError(
                "faster-whisper is not installed. Run this ORBIT install step on your Windows PC:\n"
                "  pip install -r requirements/windows.txt\n"
                "See README.md 'ASR setup' for model download instructions."
            ) from exc

        self.model_size = model_size
        self.device = device
        # Must match the download_root scripts/download_asr_model.py used --
        # otherwise the model downloaded there is never found here, and
        # faster-whisper silently re-downloads (or fails offline) instead.
        self._model = WhisperModel(
            model_size, device=device, compute_type=compute_type, download_root=str(download_root) if download_root else None
        )

    def transcribe(self, audio: AudioInput, language: Optional[str] = None) -> TranscriptionResult:
        lang = None if (language in (None, "auto")) else language
        segments_iter, info = self._model.transcribe(audio, language=lang, vad_filter=True)
        segments = []
        full_text_parts = []
        for seg in segments_iter:
            segments.append(
                TranscriptSegment(
                    text=seg.text.strip(),
                    start=seg.start,
                    end=seg.end,
                    confidence=float(getattr(seg, "avg_logprob", 0.0) or 0.0),
                )
            )
            full_text_parts.append(seg.text.strip())

        return TranscriptionResult(
            raw_text=" ".join(full_text_parts).strip(),
            language=info.language,
            segments=segments,
            confidence=float(getattr(info, "language_probability", 1.0) or 1.0),
            engine=self.name,
        )
