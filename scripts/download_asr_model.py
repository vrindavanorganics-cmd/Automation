#!/usr/bin/env python3
"""Explicit, user-initiated ASR model download.

ORBIT never downloads a large model automatically. Run this script on your
Windows PC (after requirements/windows.txt is installed) to fetch a
faster-whisper model. Requires internet access.

Usage:
    python scripts/download_asr_model.py --size small
    python scripts/download_asr_model.py --list
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orbit.config import settings
from orbit.models.manager import CATALOG, ModelManager
from orbit.windows.hardware import detect_hardware, recommend_asr_model


def main() -> None:
    parser = argparse.ArgumentParser(description="Download a local ASR (faster-whisper) model")
    parser.add_argument("--size", choices=[m.name for m in CATALOG], help="Model size to download")
    parser.add_argument("--list", action="store_true", help="List available models and recommendation, then exit")
    parser.add_argument("--yes", action="store_true", help="Skip the confirmation prompt")
    args = parser.parse_args()

    manager = ModelManager(settings.data_dir / "models")
    hw = detect_hardware()
    recommended = recommend_asr_model(hw)

    if args.list or not args.size:
        print(f"Detected hardware: {hw.os_name} | {hw.cpu_cores} cores | {hw.ram_gb} GB RAM | GPU: {hw.gpu or 'none detected'}")
        print(f"Recommended model for this machine: {recommended}\n")
        print(f"{'name':<10} {'size_mb':>8} {'min_ram_gb':>11} {'speed':<15} installed")
        for row in manager.list_models(hw):
            print(f"{row['name']:<10} {row['size_mb']:>8} {row['min_ram_gb']:>11} {row['speed']:<15} {row['installed']}")
        if not args.size:
            return

    size = args.size
    spec = next(m for m in CATALOG if m.name == size)
    if not args.yes:
        answer = input(
            f"Download '{size}' (~{spec.size_mb} MB, needs ~{spec.min_ram_gb} GB RAM)? [y/N]: "
        ).strip().lower()
        if answer not in ("y", "yes"):
            print("Cancelled.")
            return

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print(
            "faster-whisper is not installed. Run:\n  pip install -r requirements/windows.txt",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Downloading '{size}'... (this contacts huggingface.co)")
    WhisperModel(size, device="cpu", download_root=str(settings.data_dir / "models" / size))
    manager.mark_installed(size)
    print(f"Done. '{size}' is installed. Set ORBIT_ASR_MODEL_SIZE={size} in .env to use it.")


if __name__ == "__main__":
    main()
