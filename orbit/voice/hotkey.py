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
    """Registers a real global hotkey via the `keyboard` package.
    LOCAL WINDOWS TEST NEEDED — requires requirements/windows.txt and,
    on Windows, typically an elevated/admin process to capture all key
    events system-wide.
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
        self.on_press = on_press
        self.on_release = on_release
        self._registered = False

    def start(self) -> None:
        self._keyboard.add_hotkey(self.hotkey, self.on_press)
        self._registered = True

    def stop(self) -> None:
        if self._registered:
            self._keyboard.remove_hotkey(self.hotkey)
            self._registered = False
