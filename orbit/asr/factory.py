"""Factory for constructing the configured ASR engine."""
from __future__ import annotations

from orbit.asr.base import ASREngine
from orbit.config import Settings


def get_asr_engine(settings: Settings, force_mock: bool = False) -> ASREngine:
    if force_mock or settings.asr_engine == "mock":
        from orbit.asr.mock_engine import MockASREngine

        return MockASREngine()

    if settings.asr_engine == "faster-whisper":
        from orbit.asr.whisper_engine import FasterWhisperEngine

        download_root = settings.data_dir / "models" / settings.asr_model_size
        return FasterWhisperEngine(
            model_size=settings.asr_model_size, device=settings.asr_device, download_root=download_root
        )

    raise ValueError(f"Unknown ASR engine: {settings.asr_engine}")
