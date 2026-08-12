"""Minimal text-mode interface for ORBIT.

This is the primary way to exercise the full VOICE(text)->UNDERSTAND->PLAN
->ACT->VERIFY->RESPOND loop inside the browser Claude Code workspace, where
there is no microphone, no global hotkey, and no real Windows desktop. On
the user's actual Windows PC, this same brain is driven by voice instead
(see main.py / orbit/ui/tray.py).
"""
from __future__ import annotations

import sys

from orbit.bootstrap import OrbitSystem, build_orbit
from orbit.permissions.engine import ConfirmationRequest


def cli_confirm(request: ConfirmationRequest) -> bool:
    print(f"\n[CONFIRM NEEDED] {request.description}")
    if request.details:
        print(f"  details: {request.details}")
    answer = input("  Proceed? [y/N]: ").strip().lower()
    return answer in ("y", "yes")


def run_repl(system: OrbitSystem) -> None:
    print("ORBIT — text mode (type a command, or 'quit' to exit)")
    backend = system.controller.backend_name
    if backend == "real-windows":
        print("Computer control backend: real-windows (apps will actually launch)")
    else:
        print(
            f"Computer control backend: {backend} -- NOTHING will actually open on your PC. "
            "Commands like 'open chrome' will only print text.\n"
            "Run 'python scripts\\check_windows_control.py' to find out why."
        )
    print("Examples: 'open chrome', 'create a folder called Buyer Leads', 'orbit, stop'\n")
    while True:
        try:
            raw = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not raw:
            continue
        if raw.lower() in ("quit", "exit"):
            break

        response = system.brain.process_text_command(raw)
        print(f"orbit> {response.text}")
        if response.plan and len(response.plan.steps) > 1:
            print(f"  (plan: {[s.description for s in response.plan.steps]})")


def main() -> None:
    system = build_orbit(confirm_callback=cli_confirm, force_mock_asr=True)
    try:
        run_repl(system)
    finally:
        system.shutdown()


if __name__ == "__main__":
    sys.exit(main() or 0)
