"""RealHotkeyListener's hold-to-talk logic, exercised against a fake
`keyboard` module (the real one needs OS-level hooks unavailable here).
"""
from __future__ import annotations

import sys
import types
from dataclasses import dataclass

import pytest


@dataclass
class FakeKeyEvent:
    name: str
    event_type: str


class FakeKeyboardModule:
    def __init__(self):
        self._callback = None

    def hook(self, callback):
        self._callback = callback
        return callback

    def unhook(self, handle):
        self._callback = None

    def fire(self, name: str, event_type: str) -> None:
        self._callback(FakeKeyEvent(name=name, event_type=event_type))


@pytest.fixture
def fake_keyboard(monkeypatch):
    fake = FakeKeyboardModule()
    module = types.ModuleType("keyboard")
    module.hook = fake.hook
    module.unhook = fake.unhook
    monkeypatch.setitem(sys.modules, "keyboard", module)
    return fake


def _make_listener(fake_keyboard, hotkey="ctrl+shift+space"):
    from orbit.voice.hotkey import RealHotkeyListener

    presses = []
    releases = []
    listener = RealHotkeyListener(hotkey, on_press=lambda: presses.append(1), on_release=lambda: releases.append(1))
    listener.start()
    return listener, presses, releases


def test_fires_on_press_only_once_all_keys_down(fake_keyboard):
    listener, presses, releases = _make_listener(fake_keyboard)
    fake_keyboard.fire("ctrl", "down")
    assert presses == []
    fake_keyboard.fire("shift", "down")
    assert presses == []
    fake_keyboard.fire("space", "down")
    assert presses == [1]
    assert releases == []


def test_fires_on_release_when_any_key_lifts(fake_keyboard):
    listener, presses, releases = _make_listener(fake_keyboard)
    for key in ("ctrl", "shift", "space"):
        fake_keyboard.fire(key, "down")
    assert presses == [1]

    fake_keyboard.fire("space", "up")
    assert releases == [1]


def test_does_not_refire_press_while_already_held(fake_keyboard):
    listener, presses, releases = _make_listener(fake_keyboard)
    for key in ("ctrl", "shift", "space"):
        fake_keyboard.fire(key, "down")
    fake_keyboard.fire("space", "up")
    fake_keyboard.fire("space", "down")
    assert presses == [1, 1]
    assert releases == [1]


def test_ignores_unrelated_keys(fake_keyboard):
    listener, presses, releases = _make_listener(fake_keyboard)
    fake_keyboard.fire("a", "down")
    fake_keyboard.fire("b", "up")
    assert presses == []
    assert releases == []


def test_stop_unhooks(fake_keyboard):
    listener, presses, releases = _make_listener(fake_keyboard)
    listener.stop()
    assert fake_keyboard._callback is None
