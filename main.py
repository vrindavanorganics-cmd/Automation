#!/usr/bin/env python3
"""ORBIT entrypoint.

    python main.py --text     Text-mode REPL (works anywhere, including this
                               browser workspace — no mic/hotkey/tray needed)
    python main.py --voice    Real voice loop: global hotkey + microphone +
                               local ASR + system tray. LOCAL WINDOWS TEST
                               NEEDED — requires requirements/windows.txt
                               and an actual Windows desktop/microphone.
"""
from __future__ import annotations

import argparse
import sys
import time

from orbit.bootstrap import build_orbit
from orbit.config import settings
from orbit.permissions.engine import ConfirmationRequest


def run_text_mode() -> None:
    from orbit.ui.cli import cli_confirm, run_repl

    system = build_orbit(confirm_callback=cli_confirm, force_mock_asr=True)
    try:
        run_repl(system)
    finally:
        system.shutdown()


def run_voice_mode() -> None:
    """Real push-to-talk voice loop. Requires Windows + requirements/windows.txt.
    Fails fast with a clear message if run anywhere else — it does not
    pretend to control a desktop that isn't there.
    """
    import platform

    if platform.system() != "Windows":
        print(
            "ERROR: --voice mode requires a real Windows desktop with a microphone.\n"
            f"Detected platform: {platform.system()}.\n"
            "Use 'python main.py --text' to exercise ORBIT's pipeline here instead.\n"
            "See README.md 'Running ORBIT' for local Windows setup.",
            file=sys.stderr,
        )
        sys.exit(1)

    from orbit.voice.hotkey import RealHotkeyListener
    from orbit.voice.recorder import RealAudioRecorder

    def cli_confirm(request: ConfirmationRequest) -> bool:
        print(f"\n[CONFIRM NEEDED] {request.description}")
        return input("  Proceed? [y/N]: ").strip().lower() in ("y", "yes")

    system = build_orbit(confirm_callback=cli_confirm, browser_headless=False)
    recorder = RealAudioRecorder()

    from orbit.ui.tray import TrayState

    state = TrayState()

    def on_press() -> None:
        state.set_listening()
        print("Listening...")
        recorder.start()

    def on_release() -> None:
        audio_bytes = recorder.stop()
        state.set_ready()
        if not audio_bytes:
            print("(heard nothing -- try holding the hotkey a bit longer)")
            return
        wav_path = system.settings.data_dir / "last_command.wav"
        recorder.save_wav(wav_path, audio_bytes)
        try:
            response = system.brain.process_voice_command(str(wav_path))
            print(f"orbit> {response.text}")
            state.set_transcript(response.text)
            state.push_history(response.text)
        except Exception as exc:  # one bad turn must not kill the whole voice loop
            print(f"(error handling that command: {exc})", file=sys.stderr)
            state.push_history(f"Error: {exc}")

    listener = RealHotkeyListener(settings.hotkey, on_press=on_press, on_release=on_release)

    try:
        _run_with_tray(state, listener, settings.hotkey)
    except KeyboardInterrupt:
        pass
    finally:
        listener.stop()
        system.shutdown()


def _run_with_tray(state, listener, hotkey: str) -> None:
    """Runs the tray icon (blocking) with the hotkey listener wired to its
    Stop/History/Settings menu. Falls back to a plain console loop if
    pystray/Pillow aren't installed, so --voice still works without the
    tray -- it just prints instead of showing a tray icon.
    """
    from orbit.ui.tray import build_tray_icon

    icon_box: dict = {}

    def on_stop() -> None:
        listener.stop()
        icon = icon_box.get("icon")
        if icon:
            icon.stop()

    def on_history() -> None:
        lines = "\n".join(state.history_preview) or "No commands yet."
        icon = icon_box.get("icon")
        if icon:
            icon.notify(lines, "ORBIT recent activity")
        print(lines)

    def on_settings() -> None:
        text = (
            f"Hotkey: {settings.hotkey}\n"
            f"ASR: {settings.asr_engine} ({settings.asr_model_size})\n"
            f"Chrome profile: {settings.chrome_profile or 'picker each time'}"
        )
        icon = icon_box.get("icon")
        if icon:
            icon.notify(text, "ORBIT settings")
        print(text)

    try:
        icon = build_tray_icon(state, on_stop=on_stop, on_history=on_history, on_settings=on_settings)
    except RuntimeError as exc:
        print(f"(tray icon unavailable: {exc})", file=sys.stderr)
        print(f"ORBIT is running. Hold {hotkey} to talk. Ctrl+C to quit.")
        listener.start()
        while True:
            time.sleep(0.2)

    icon_box["icon"] = icon

    def setup(icon) -> None:
        icon.visible = True
        listener.start()
        try:
            import keyboard  # type: ignore

            keyboard.add_hotkey("esc", on_stop)
        except Exception:
            pass  # Esc-to-stop is a convenience, not required
        print(f"ORBIT is running in the system tray. Hold {hotkey} to talk. Esc or the tray menu stops it.")

    icon.run(setup=setup)


def main() -> None:
    parser = argparse.ArgumentParser(description="ORBIT — personal voice AI computer agent")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--text", action="store_true", help="Run in text-mode REPL (default)")
    mode.add_argument("--voice", action="store_true", help="Run real voice loop (Windows only)")
    args = parser.parse_args()

    if args.voice:
        run_voice_mode()
    else:
        run_text_mode()


if __name__ == "__main__":
    main()
