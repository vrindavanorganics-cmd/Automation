"""FasterWhisperEngine's download_root plumbing, exercised against a fake
`faster_whisper` module (the real one needs a network download / real
model files unavailable here).

Regression: scripts/download_asr_model.py downloads into
settings.data_dir/models/<size>, but FasterWhisperEngine used to construct
WhisperModel() with no download_root at all, so it would look in the
default huggingface cache instead and never find what was downloaded.
"""
from __future__ import annotations

import sys
import types

import pytest


@pytest.fixture
def fake_faster_whisper(monkeypatch):
    calls = []

    class FakeWhisperModel:
        def __init__(self, model_size, device=None, compute_type=None, download_root=None):
            calls.append(
                {
                    "model_size": model_size,
                    "device": device,
                    "compute_type": compute_type,
                    "download_root": download_root,
                }
            )

    module = types.ModuleType("faster_whisper")
    module.WhisperModel = FakeWhisperModel
    monkeypatch.setitem(sys.modules, "faster_whisper", module)
    return calls


def test_passes_download_root_through_to_whisper_model(fake_faster_whisper):
    from orbit.asr.whisper_engine import FasterWhisperEngine

    FasterWhisperEngine(model_size="small", download_root="/data/models/small")

    assert fake_faster_whisper[-1]["download_root"] == "/data/models/small"


def test_factory_points_download_root_at_the_configured_model_dir(fake_faster_whisper, tmp_path, monkeypatch):
    from orbit.asr.factory import get_asr_engine
    from orbit.config import Settings

    settings = Settings(data_dir=tmp_path, asr_engine="faster-whisper", asr_model_size="small")
    get_asr_engine(settings)

    assert fake_faster_whisper[-1]["download_root"] == str(tmp_path / "models" / "small")
