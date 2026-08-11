"""Model Manager: tracks available/installed ASR models and recommends one
based on detected hardware. Never auto-downloads a large model — download is
always an explicit, user-initiated step.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from orbit.windows.hardware import HardwareInfo, detect_hardware


@dataclass
class ModelSpec:
    name: str
    size_mb: int
    min_ram_gb: float
    min_vram_gb: Optional[float]
    relative_speed: str  # "fastest" | "fast" | "balanced" | "accurate" | "most accurate"


CATALOG: list[ModelSpec] = [
    ModelSpec("tiny", 75, 2.0, None, "fastest"),
    ModelSpec("base", 145, 3.0, None, "fast"),
    ModelSpec("small", 480, 4.0, None, "balanced"),
    ModelSpec("medium", 1500, 8.0, 5.0, "accurate"),
    ModelSpec("large-v3", 3100, 12.0, 10.0, "most accurate"),
]


class ModelManager:
    def __init__(self, models_dir: Path | str, active_model: Optional[str] = None):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self._active_model = active_model

    def _model_path(self, name: str) -> Path:
        return self.models_dir / name

    def is_installed(self, name: str) -> bool:
        return self._model_path(name).exists()

    def list_models(self, hw: Optional[HardwareInfo] = None) -> list[dict]:
        hw = hw or detect_hardware()
        rows = []
        for spec in CATALOG:
            rows.append(
                {
                    "name": spec.name,
                    "size_mb": spec.size_mb,
                    "min_ram_gb": spec.min_ram_gb,
                    "min_vram_gb": spec.min_vram_gb,
                    "speed": spec.relative_speed,
                    "fits_hardware": hw.ram_gb >= spec.min_ram_gb,
                    "installed": self.is_installed(spec.name),
                    "active": spec.name == self._active_model,
                }
            )
        return rows

    def set_active(self, name: str) -> None:
        if name not in {s.name for s in CATALOG}:
            raise ValueError(f"Unknown model '{name}'")
        self._active_model = name

    def get_active(self) -> Optional[str]:
        return self._active_model

    def mark_installed(self, name: str) -> None:
        """Called after a real download completes (local Windows step —
        actual model download requires network + disk and is not performed
        automatically). Creates a marker file so Model Manager tracks state.
        """
        self._model_path(name).mkdir(parents=True, exist_ok=True)
        (self._model_path(name) / ".installed").write_text("1")
