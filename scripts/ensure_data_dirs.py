#!/usr/bin/env python3
"""Creates ORBIT's local data directories and prints where they are.

Kept as a standalone script (rather than an inline `python -c "..."` in
setup_windows.ps1) because Windows PowerShell 5.1's argument parsing for
external commands can mangle one-liners containing a mix of nested quotes
and commas -- this avoids that entirely.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orbit.config import settings

print(f"Data directory ready at {settings.data_dir}")
