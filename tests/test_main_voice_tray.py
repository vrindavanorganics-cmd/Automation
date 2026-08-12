"""main.py's _run_with_tray(): wires the tray icon's Stop/History/Settings
menu to the hotkey listener, and falls back to a plain console loop if
pystray/Pillow aren't installed (both are exercised without a real display
or a real hotkey backend).
"""
from __future__ import annotations

import time

import pytest

import main
from orbit.ui.tray import TrayState


class FakeListener:
    def __init__(self):
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


class _StopLoop(Exception):
    pass


def test_falls_back_to_console_loop_when_tray_unavailable(monkeypatch):
    monkeypatch.setattr(
        "orbit.ui.tray.build_tray_icon",
        lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("pystray missing")),
    )
    calls = {"n": 0}

    def fake_sleep(_):
        calls["n"] += 1
        raise _StopLoop

    monkeypatch.setattr(time, "sleep", fake_sleep)

    listener = FakeListener()
    state = TrayState()
    with pytest.raises(_StopLoop):
        main._run_with_tray(state, listener, "ctrl+shift+space")

    assert listener.started is True
    assert calls["n"] == 1


class FakeIcon:
    def __init__(self):
        self.visible = False
        self.stopped = False
        self.notifications = []

    def run(self, setup):
        setup(self)

    def stop(self):
        self.stopped = True

    def notify(self, message, title=None):
        self.notifications.append((title, message))


def test_stop_menu_action_stops_listener_and_icon(monkeypatch):
    fake_icon = FakeIcon()
    captured = {}

    def fake_build_tray_icon(state, on_stop, on_history, on_settings):
        captured["on_stop"] = on_stop
        captured["on_history"] = on_history
        captured["on_settings"] = on_settings
        return fake_icon

    monkeypatch.setattr("orbit.ui.tray.build_tray_icon", fake_build_tray_icon)

    listener = FakeListener()
    state = TrayState()
    state.push_history("open chrome")
    main._run_with_tray(state, listener, "ctrl+shift+space")

    assert listener.started is True
    assert fake_icon.visible is True

    captured["on_history"]()
    assert fake_icon.notifications  # a notification was shown with recent activity

    captured["on_stop"]()
    assert listener.stopped is True
    assert fake_icon.stopped is True
