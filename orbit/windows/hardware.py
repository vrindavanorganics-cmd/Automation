"""Local hardware detection, used to recommend an appropriately-sized ASR model.

Runs cross-platform (uses psutil + platform), so it's fully testable here in
the browser workspace even though the actual recommendation matters most on
the user's real Windows PC.
"""
from __future__ import annotations

import platform
import subprocess
from dataclasses import dataclass
from typing import Optional

import psutil


@dataclass
class HardwareInfo:
    os_name: str
    os_version: str
    cpu: str
    cpu_cores: int
    ram_gb: float
    gpu: Optional[str]
    vram_gb: Optional[float]


def _detect_gpu() -> tuple[Optional[str], Optional[float]]:
    """Best-effort NVIDIA GPU detection via nvidia-smi. Returns (name, vram_gb).
    Returns (None, None) if no NVIDIA GPU/driver is present — this is normal
    and expected on most laptops, including inside this browser workspace.
    """
    try:
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL,
            timeout=3,
        ).decode()
        line = output.strip().splitlines()[0]
        name, mem_mb = [p.strip() for p in line.split(",")]
        return name, round(float(mem_mb) / 1024, 1)
    except Exception:
        return None, None


def detect_hardware() -> HardwareInfo:
    gpu, vram = _detect_gpu()
    return HardwareInfo(
        os_name=platform.system(),
        os_version=platform.version(),
        cpu=platform.processor() or platform.machine(),
        cpu_cores=psutil.cpu_count(logical=True) or 1,
        ram_gb=round(psutil.virtual_memory().total / (1024**3), 1),
        gpu=gpu,
        vram_gb=vram,
    )


# (model_size, min_ram_gb) — ordered smallest to largest.
_ASR_MODEL_REQUIREMENTS = [
    ("tiny", 2.0),
    ("base", 3.0),
    ("small", 4.0),
    ("medium", 8.0),
    ("large-v3", 12.0),
]


def recommend_asr_model(hw: Optional[HardwareInfo] = None) -> str:
    """Conservative recommendation — never suggests a model requiring more
    RAM than the machine has. Does not consider GPU (CPU-safe by default);
    a GPU with enough VRAM lets the user manually pick a larger model in
    the Model Manager.
    """
    hw = hw or detect_hardware()
    best = "tiny"
    for size, min_ram in _ASR_MODEL_REQUIREMENTS:
        if hw.ram_gb >= min_ram:
            best = size
        else:
            break
    return best
