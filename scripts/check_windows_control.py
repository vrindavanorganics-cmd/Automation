#!/usr/bin/env python3
"""Diagnoses whether ORBIT can actually control this Windows PC, or is
silently falling back to the SIMULATED backend (which only prints text and
never launches anything real).

Usage:
    python scripts\\check_windows_control.py
    python scripts\\check_windows_control.py --launch-test   # also opens Notepad as a live test
"""
from __future__ import annotations

import argparse
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _check_import(module_name: str) -> tuple[bool, str]:
    try:
        __import__(module_name)
        return True, "OK"
    except Exception as exc:  # noqa: BLE001 - diagnostic script, want the exact error
        return False, f"{type(exc).__name__}: {exc}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose ORBIT's Windows computer-control backend")
    parser.add_argument(
        "--launch-test", action="store_true", help="Also try actually launching Notepad as a live test"
    )
    args = parser.parse_args()

    print(f"Platform: {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Python:   {sys.version.split()[0]} at {sys.executable}")
    print()

    if platform.system() != "Windows":
        print(
            "This is not a Windows machine, so ORBIT will always use the SIMULATED "
            "backend here -- that's expected in this environment, not a bug."
        )
        return

    print("Checking required packages (from requirements/windows.txt):")
    all_ok = True
    for module_name, pip_name in [
        ("pyautogui", "pyautogui"),
        ("pygetwindow", "pygetwindow"),
        ("pyperclip", "pyperclip"),
    ]:
        ok, detail = _check_import(module_name)
        all_ok = all_ok and ok
        status = "OK" if ok else "MISSING/BROKEN"
        print(f"  [{status:15}] {module_name:12} ({pip_name}) -- {detail}")

    print()
    if not all_ok:
        print(
            "One or more packages failed to import. This is why ORBIT falls back to the\n"
            "SIMULATED backend -- it prints 'Launched X' but nothing actually opens.\n\n"
            "Fix: run this in your project folder with the virtual environment active:\n"
            "  .\\.venv\\Scripts\\Activate.ps1\n"
            "  pip install -r requirements\\windows.txt\n"
            "Then re-run this diagnostic."
        )
        return

    from orbit.windows.control import RealWindowsController

    try:
        controller = RealWindowsController()
    except RuntimeError as exc:
        print(f"Packages imported fine, but RealWindowsController still failed to start: {exc}")
        return

    print("RealWindowsController started successfully -- ORBIT can control this PC for real.")
    windows = controller.list_windows()
    print(f"Currently {len(windows)} window(s) open, e.g.: {windows[:5]}")

    if args.launch_test:
        print("\nLaunching Notepad as a live test...")
        ok = controller.launch_app("notepad.exe")
        print("Popen call succeeded." if ok else "Popen call FAILED.")
        print("Check your taskbar now -- if Notepad did not actually appear, something below")
        print("Python (antivirus, Group Policy, a sandboxed shell) is blocking process launches.")


if __name__ == "__main__":
    main()
