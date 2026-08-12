"""Central configuration for ORBIT.

All configuration comes from environment variables (optionally loaded from a
local .env file). No secrets are ever hardcoded here.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # python-dotenv is a base dependency, but ORBIT must not hard-crash if it
    # is momentarily missing (e.g. partial install) — env vars still work.
    pass

ROOT_DIR = Path(__file__).resolve().parent.parent


def _bool_env(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("ORBIT_DATA_DIR", "./data")).resolve()
    )

    llm_provider: str = field(default_factory=lambda: os.environ.get("ORBIT_LLM_PROVIDER", "anthropic"))
    llm_model: str = field(default_factory=lambda: os.environ.get("ORBIT_LLM_MODEL", "claude-sonnet-5"))
    anthropic_api_key: str | None = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY") or None)
    openai_api_key: str | None = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY") or None)

    asr_engine: str = field(default_factory=lambda: os.environ.get("ORBIT_ASR_ENGINE", "faster-whisper"))
    asr_model_size: str = field(default_factory=lambda: os.environ.get("ORBIT_ASR_MODEL_SIZE", "small"))
    asr_device: str = field(default_factory=lambda: os.environ.get("ORBIT_ASR_DEVICE", "cpu"))
    asr_language: str = field(default_factory=lambda: os.environ.get("ORBIT_ASR_LANGUAGE", "auto"))

    require_confirmation: bool = field(default_factory=lambda: _bool_env("ORBIT_REQUIRE_CONFIRMATION", True))
    force_simulated_controller: bool = field(
        default_factory=lambda: _bool_env("ORBIT_FORCE_SIMULATED", False)
    )
    hotkey: str = field(default_factory=lambda: os.environ.get("ORBIT_HOTKEY", "ctrl+shift+space"))

    # If set (e.g. "Vrindavan Organics"), ORBIT drives that real, already
    # signed-in Chrome profile directly instead of showing Chrome's profile
    # picker each time. Leave unset to have Chrome ask which profile to use.
    chrome_profile: str | None = field(default_factory=lambda: os.environ.get("ORBIT_CHROME_PROFILE") or None)

    def __post_init__(self) -> None:
        if not isinstance(self.data_dir, Path):
            object.__setattr__(self, "data_dir", Path(self.data_dir).resolve())
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "memory").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "skills").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "history").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "models").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "vocab").mkdir(parents=True, exist_ok=True)


settings = Settings()
