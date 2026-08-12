"""Global hotkey abstraction for push-to-talk.

SimulatedHotkeyListener: testable anywhere — call `.trigger()` manually
(used by tests and by the desktop UI's on-screen mic button).

RealHotkeyListener: registers an OS-level global hotkey via the `keyboard`
library. Windows-only in practice (the `keyboard` library needs elevated
permissions on Linux); NOT exercised in this browser workspace.
"""
from __future__ import annotations

from typing import Callable, Optional

Callback = Callable[[], None]


class HotkeyListener:
    def start(self) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError


class SimulatedHotkeyListener(HotkeyListener):
    def __init__(self, hotkey: str, on_press: Callback, on_release: Optional[Callback] = None):
        self.hotkey = hotkey
        self.on_press = on_press
        self.on_release = on_release
        self.running = False
        self.trigger_count = 0

    def start(self) -> None:
        self.running = True

    def stop(self) -> None:
        self.running = False

    def trigger(self) -> None:
        """Manually fire the hotkey — used by tests and the on-screen mic button."""
        self.trigger_count += 1
        self.on_press()
        if self.on_release:
            self.on_release()


class RealHotkeyListener(HotkeyListener):
    """Registers a real global *hold-to-talk* hotkey via the `keyboard`
    package. LOCAL WINDOWS TEST NEEDED — requires requirements/windows.txt
    and, on Windows, typically an elevated/admin process to capture all key
    events system-wide.

    `keyboard.add_hotkey()` only fires once when a combo completes -- it has
    no notion of "still held down", so it cannot drive push-to-talk (record
    while held, stop on release). Instead this hooks raw key events and
    tracks which of the hotkey's own keys are currently down, firing
    `on_press` the moment all of them are down and `on_release` the moment
    any of them comes back up.
    """

    def __init__(self, hotkey: str, on_press: Callback, on_release: Optional[Callback] = None):
        try:
            import keyboard  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "The 'keyboard' package is required for global hotkeys. "
                "Run: pip install -r requirements/windows.txt"
            ) from exc
        self._keyboard = keyboard
        self.hotkey = hotkey
        self._keys = [part.strip().lower() for part in hotkey.split("+") if part.strip()]
        self.on_press = on_press
        self.on_release = on_release
        self._pressed: set[str] = set()
        self._active = False
        self._hook = None

    def _on_event(self, event) -> None:
        name = (event.name or "").lower()
        if name not in self._keys:
            return
        if event.event_type == "down":
            self._pressed.add(name)
        elif event.event_type == "up":
            self._pressed.discard(name)

        all_down = all(k in self._pressed for k in self._keys)
        if all_down and not self._active:
            self._active = True
            self.on_press()
        elif not all_down and self._active:
            self._active = False
            if self.on_release:
                self.on_release()

    def start(self) -> None:
        self._pressed = set()
        self._active = False
        self._hook = self._keyboard.hook(self._on_event)

    def stop(self) -> None:
        if self._hook is not None:
            self._keyboard.unhook(self._hook)
            self._hook = None
