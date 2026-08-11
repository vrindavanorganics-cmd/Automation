"""Minimal Windows system tray UI for ORBIT.

    ORBIT
    ● Listening / ○ Ready
    Transcript
    Current task
    Progress
    Stop
    History
    Settings

Uses `pystray` + `Pillow` for the tray icon. LOCAL WINDOWS TEST NEEDED —
tray icons cannot be rendered in this headless browser workspace. The
status-window content and menu wiring below are real code, exercised only
by unit tests on the underlying state (see tests/test_tray_state.py), not
by an actual rendered tray icon.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class OrbitStatus(str, Enum):
    READY = "Ready"
    LISTENING = "Listening"
    THINKING = "Thinking"
    ACTING = "Acting"
    STOPPED = "Stopped"


@dataclass
class TrayState:
    """Plain-data state for the tray UI — kept separate from the actual
    pystray rendering so it's testable without a display.
    """

    status: OrbitStatus = OrbitStatus.READY
    transcript: str = ""
    current_task: str = ""
    progress: str = ""
    history_preview: list[str] = field(default_factory=list)

    def set_listening(self) -> None:
        self.status = OrbitStatus.LISTENING

    def set_ready(self) -> None:
        self.status = OrbitStatus.READY
        self.current_task = ""
        self.progress = ""

    def set_task(self, task: str) -> None:
        self.status = OrbitStatus.ACTING
        self.current_task = task

    def set_transcript(self, text: str) -> None:
        self.transcript = text

    def push_history(self, entry: str, limit: int = 5) -> None:
        self.history_preview.insert(0, entry)
        self.history_preview = self.history_preview[:limit]


def build_tray_icon(
    state: TrayState,
    on_stop: Callable[[], None],
    on_history: Callable[[], None],
    on_settings: Callable[[], None],
):
    """Builds the real pystray Icon. Only callable on a machine with a
    desktop environment (Windows locally). Raises a clear error elsewhere.
    """
    try:
        import pystray  # type: ignore
        from PIL import Image, ImageDraw  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "pystray/Pillow are required for the system tray UI. "
            "Run: pip install -r requirements/windows.txt"
        ) from exc

    def _make_image(color: str):
        img = Image.new("RGB", (64, 64), "black")
        draw = ImageDraw.Draw(img)
        draw.ellipse((16, 16, 48, 48), fill=color)
        return img

    def _status_label(item=None) -> str:
        dot = "●" if state.status == OrbitStatus.LISTENING else "○"
        return f"{dot} {state.status.value}"

    menu = pystray.Menu(
        pystray.MenuItem(_status_label, None, enabled=False),
        pystray.MenuItem(lambda item: f"Task: {state.current_task or '-'}", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Stop", lambda item: on_stop()),
        pystray.MenuItem("History", lambda item: on_history()),
        pystray.MenuItem("Settings", lambda item: on_settings()),
    )

    icon_color = "red" if state.status == OrbitStatus.LISTENING else "green"
    icon = pystray.Icon("orbit", _make_image(icon_color), "ORBIT", menu)
    return icon
