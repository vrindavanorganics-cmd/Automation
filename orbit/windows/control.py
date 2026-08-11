"""Windows computer-control abstraction.

Two implementations:
  - SimulatedController: pure-Python, works on any OS (Linux/Mac/Windows).
    This is what runs in the browser Claude Code workspace and in tests —
    it maintains an in-memory model of "open windows" and logs every
    action so the full ORBIT pipeline can be exercised end to end without
    a real desktop.
  - RealWindowsController: uses pyautogui/pywinauto/pygetwindow/pyperclip
    to actually control a Windows PC. Only importable/usable on Windows
    with requirements/windows.txt installed. NOT exercised in this browser
    workspace — requires local Windows testing (see README).

get_controller() picks the right one automatically.
"""
from __future__ import annotations

import platform
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class ActionLogEntry:
    timestamp: float
    action: str
    params: dict


class WindowsController:
    """Abstract computer-control interface."""

    backend_name = "abstract"

    def launch_app(self, executable: str, args: Optional[list[str]] = None) -> bool:
        raise NotImplementedError

    def close_app(self, app_name: str) -> bool:
        raise NotImplementedError

    def list_windows(self) -> list[str]:
        raise NotImplementedError

    def focus_window(self, app_name: str) -> bool:
        raise NotImplementedError

    def key_press(self, keys: str) -> bool:
        raise NotImplementedError

    def type_text(self, text: str) -> bool:
        raise NotImplementedError

    def mouse_click(self, x: int, y: int, button: str = "left") -> bool:
        raise NotImplementedError

    def mouse_move(self, x: int, y: int) -> bool:
        raise NotImplementedError

    def get_clipboard(self) -> str:
        raise NotImplementedError

    def set_clipboard(self, text: str) -> bool:
        raise NotImplementedError

    def screenshot(self, path: str) -> bool:
        raise NotImplementedError


class SimulatedController(WindowsController):
    """In-memory simulated desktop for development/testing off Windows."""

    backend_name = "simulated"

    def __init__(self) -> None:
        self._open_windows: list[str] = []
        self._clipboard: str = ""
        self.action_log: list[ActionLogEntry] = []

    def _log(self, action: str, **params) -> None:
        self.action_log.append(ActionLogEntry(timestamp=time.time(), action=action, params=params))

    def launch_app(self, executable: str, args: Optional[list[str]] = None) -> bool:
        self._log("launch_app", executable=executable, args=args or [])
        if executable not in self._open_windows:
            self._open_windows.append(executable)
        return True

    def close_app(self, app_name: str) -> bool:
        self._log("close_app", app_name=app_name)
        before = len(self._open_windows)
        self._open_windows = [w for w in self._open_windows if app_name.lower() not in w.lower()]
        return len(self._open_windows) < before

    def list_windows(self) -> list[str]:
        return list(self._open_windows)

    def focus_window(self, app_name: str) -> bool:
        self._log("focus_window", app_name=app_name)
        return any(app_name.lower() in w.lower() for w in self._open_windows)

    def key_press(self, keys: str) -> bool:
        self._log("key_press", keys=keys)
        return True

    def type_text(self, text: str) -> bool:
        self._log("type_text", text=text)
        return True

    def mouse_click(self, x: int, y: int, button: str = "left") -> bool:
        self._log("mouse_click", x=x, y=y, button=button)
        return True

    def mouse_move(self, x: int, y: int) -> bool:
        self._log("mouse_move", x=x, y=y)
        return True

    def get_clipboard(self) -> str:
        return self._clipboard

    def set_clipboard(self, text: str) -> bool:
        self._clipboard = text
        self._log("set_clipboard", length=len(text))
        return True

    def screenshot(self, path: str) -> bool:
        # Writes a tiny placeholder file so file-existence verification works
        # in tests/dev without needing a real display.
        self._log("screenshot", path=path)
        with open(path, "wb") as f:
            f.write(b"SIMULATED_SCREENSHOT")
        return True


class RealWindowsController(WindowsController):
    """Real Windows desktop control via pyautogui / pywinauto / pygetwindow.

    Requires requirements/windows.txt. Cannot be imported or tested in the
    browser workspace (no Windows desktop, no display). Every method here
    is LOCAL WINDOWS TEST NEEDED.
    """

    backend_name = "real-windows"

    def __init__(self) -> None:
        if platform.system() != "Windows":
            raise RuntimeError(
                "RealWindowsController can only run on Windows. "
                "Use SimulatedController for development/testing off Windows."
            )
        try:
            import pyautogui  # type: ignore
            import pygetwindow as gw  # type: ignore
            import pyperclip  # type: ignore
            import subprocess  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "Windows control dependencies missing. Run:\n"
                "  pip install -r requirements/windows.txt"
            ) from exc

        self._pyautogui = pyautogui
        self._gw = gw
        self._pyperclip = pyperclip

    def launch_app(self, executable: str, args: Optional[list[str]] = None) -> bool:
        import subprocess

        try:
            subprocess.Popen([executable, *(args or [])])
            return True
        except OSError:
            return False

    def close_app(self, app_name: str) -> bool:
        matches = [w for w in self._gw.getAllTitles() if app_name.lower() in w.lower()]
        for title in matches:
            for win in self._gw.getWindowsWithTitle(title):
                win.close()
        return bool(matches)

    def list_windows(self) -> list[str]:
        return [t for t in self._gw.getAllTitles() if t.strip()]

    def focus_window(self, app_name: str) -> bool:
        matches = [w for w in self._gw.getAllTitles() if app_name.lower() in w.lower()]
        if not matches:
            return False
        for win in self._gw.getWindowsWithTitle(matches[0]):
            win.activate()
            return True
        return False

    def key_press(self, keys: str) -> bool:
        self._pyautogui.hotkey(*keys.split("+"))
        return True

    def type_text(self, text: str) -> bool:
        self._pyautogui.typewrite(text)
        return True

    def mouse_click(self, x: int, y: int, button: str = "left") -> bool:
        self._pyautogui.click(x, y, button=button)
        return True

    def mouse_move(self, x: int, y: int) -> bool:
        self._pyautogui.moveTo(x, y)
        return True

    def get_clipboard(self) -> str:
        return self._pyperclip.paste()

    def set_clipboard(self, text: str) -> bool:
        self._pyperclip.copy(text)
        return True

    def screenshot(self, path: str) -> bool:
        img = self._pyautogui.screenshot()
        img.save(path)
        return True


def get_controller(force_simulated: bool = False) -> WindowsController:
    if force_simulated or platform.system() != "Windows":
        return SimulatedController()
    try:
        return RealWindowsController()
    except RuntimeError:
        return SimulatedController()
