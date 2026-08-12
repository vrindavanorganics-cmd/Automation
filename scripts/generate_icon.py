#!/usr/bin/env python3
"""Generates assets/orbit.ico for the desktop shortcut.

Best-effort only: create_desktop_shortcut.ps1 calls this and silently
continues without a custom icon if it fails for any reason (Pillow missing,
no write access, ...) -- the shortcut still works, just with the default
pythonw.exe icon.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit(0)

ROOT = Path(__file__).resolve().parent.parent
SIZES = [16, 32, 48, 64, 128, 256]


def main() -> None:
    images = []
    for size in SIZES:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        margin = max(1, size // 8)
        draw.ellipse((margin, margin, size - margin, size - margin), fill=(30, 144, 255, 255))
        images.append(img)

    out = ROOT / "assets" / "orbit.ico"
    out.parent.mkdir(parents=True, exist_ok=True)
    images[-1].save(out, format="ICO", sizes=[(s, s) for s in SIZES])


if __name__ == "__main__":
    main()
