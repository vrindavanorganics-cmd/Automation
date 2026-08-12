"""Real desktop GUI app for ORBIT -- a window with a mic button, a text
command box, live status/history, and Stop, instead of only a console or a
tray-only icon. Launched via `python main.py --gui`, or by double-clicking
the desktop shortcut scripts/create_desktop_shortcut.ps1 creates (no
PowerShell needed after that one-time setup).

Uses Tkinter (Python's stdlib GUI toolkit -- no extra dependency). LOCAL
WINDOWS TEST NEEDED for the actual window: Tkinter needs a real display,
unavailable in this browser workspace. `OrbitDesktopApp` below holds all
the actual logic (what happens on each button/text event) as plain,
Tk-independent methods so that part is unit-tested here; run_gui_mode()
is the thin Tk wiring around it.
"""
from __future__ import annotations

import sys
import threading


class OrbitDesktopApp:
    """Front-end-independent logic for the desktop app. Wraps the exact
    same OrbitSystem/OrbitBrain that --text and --voice use -- this is
    only a different front end, not a different pipeline.
    """

    def __init__(self, system, recorder=None):
        self.system = system
        self.recorder = recorder
        self._recording = False

    def submit_text(self, text: str) -> str:
        text = text.strip()
        if not text:
            return ""
        response = self.system.brain.process_text_command(text)
        return response.text

    def start_recording(self) -> None:
        if self.recorder is None or self._recording:
            return
        self._recording = True
        self.recorder.start()

    def stop_recording_and_process(self) -> str:
        if self.recorder is None or not self._recording:
            return ""
        self._recording = False
        audio_bytes = self.recorder.stop()
        if not audio_bytes:
            return "(heard nothing -- try holding the button a bit longer)"
        wav_path = self.system.settings.data_dir / "last_command.wav"
        self.recorder.save_wav(wav_path, audio_bytes)
        response = self.system.brain.process_voice_command(str(wav_path))
        return response.text

    def stop(self) -> None:
        self.system.brain.stop()


def run_gui_mode() -> None:
    """Real entry point for `python main.py --gui`. Fails fast with a
    clear message if run anywhere without a desktop -- it does not
    pretend to show a window that isn't there.
    """
    import platform

    if platform.system() != "Windows":
        print(
            "ERROR: --gui mode requires a real Windows desktop.\n"
            f"Detected platform: {platform.system()}.\n"
            "Use 'python main.py --text' to exercise ORBIT's pipeline here instead.\n"
            "See README.md 'Running ORBIT' for local Windows setup.",
            file=sys.stderr,
        )
        sys.exit(1)

    import tkinter as tk
    from tkinter import messagebox, scrolledtext

    from orbit.bootstrap import build_orbit
    from orbit.permissions.engine import ConfirmationRequest
    from orbit.voice.recorder import RealAudioRecorder

    root = tk.Tk()
    root.title("ORBIT")
    root.geometry("520x580")
    root.minsize(420, 420)

    def gui_confirm(request: ConfirmationRequest) -> bool:
        # process_text_command/process_voice_command run on a background
        # worker thread (see on_submit/on_mic_release below) -- block that
        # thread on a real Tk dialog, which must itself run on the main
        # thread, via a thread-safe handoff.
        result: dict = {}
        done = threading.Event()

        def ask() -> None:
            result["ok"] = messagebox.askyesno("ORBIT needs confirmation", request.description)
            done.set()

        root.after(0, ask)
        done.wait()
        return result.get("ok", False)

    system = build_orbit(confirm_callback=gui_confirm, browser_headless=False)
    recorder = RealAudioRecorder()
    app = OrbitDesktopApp(system, recorder=recorder)

    status_var = tk.StringVar(value="Ready")
    tk.Label(root, textvariable=status_var, font=("Segoe UI", 14, "bold")).pack(pady=(10, 4))

    history = scrolledtext.ScrolledText(root, state="disabled", wrap="word")
    history.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def log(line: str) -> None:
        history.configure(state="normal")
        history.insert("end", line + "\n")
        history.configure(state="disabled")
        history.see("end")

    def run_in_background(work, on_done) -> None:
        def worker() -> None:
            result = work()
            root.after(0, lambda: on_done(result))

        threading.Thread(target=worker, daemon=True).start()

    entry_frame = tk.Frame(root)
    entry_frame.pack(fill="x", padx=10, pady=(0, 8))
    entry = tk.Entry(entry_frame)
    entry.pack(side="left", fill="x", expand=True)

    def on_submit(event=None) -> None:
        text = entry.get()
        entry.delete(0, "end")
        if not text.strip():
            return
        log(f"you> {text}")
        status_var.set("Thinking...")

        def done(reply: str) -> None:
            log(f"orbit> {reply}")
            status_var.set("Ready")

        run_in_background(lambda: app.submit_text(text), done)

    entry.bind("<Return>", on_submit)
    tk.Button(entry_frame, text="Send", command=on_submit).pack(side="left", padx=(6, 0))

    button_frame = tk.Frame(root)
    button_frame.pack(pady=(0, 12))

    mic_button = tk.Button(button_frame, text="\U0001f3a4 Hold to talk", width=18)

    def on_mic_press(event=None) -> None:
        status_var.set("Listening...")
        app.start_recording()

    def on_mic_release(event=None) -> None:
        status_var.set("Thinking...")

        def done(reply: str) -> None:
            if reply:
                log(f"orbit> {reply}")
            status_var.set("Ready")

        run_in_background(app.stop_recording_and_process, done)

    mic_button.bind("<ButtonPress-1>", on_mic_press)
    mic_button.bind("<ButtonRelease-1>", on_mic_release)
    mic_button.pack(side="left", padx=(0, 8))

    def on_stop() -> None:
        app.stop()
        log("(stopped)")
        status_var.set("Stopped")

    tk.Button(button_frame, text="Stop", command=on_stop, width=10).pack(side="left")

    def on_close() -> None:
        system.shutdown()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    log("ORBIT is ready. Type a command and press Enter, or hold the mic button to talk.")
    root.mainloop()
