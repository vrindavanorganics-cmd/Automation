"""OrbitDesktopApp's logic (submit_text/start_recording/stop_recording_and_
process/stop), exercised against fake system/recorder objects -- the
actual Tk window needs a real display, unavailable here (see
run_gui_mode(), LOCAL WINDOWS TEST NEEDED).
"""
from __future__ import annotations

from orbit.ui.desktop_app import OrbitDesktopApp


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeBrain:
    def __init__(self):
        self.text_calls = []
        self.voice_calls = []
        self.stopped = False

    def process_text_command(self, text):
        self.text_calls.append(text)
        return FakeResponse(f"handled: {text}")

    def process_voice_command(self, path):
        self.voice_calls.append(path)
        return FakeResponse("handled voice")

    def stop(self):
        self.stopped = True


class FakeSettings:
    def __init__(self, tmp_path):
        self.data_dir = tmp_path


class FakeSystem:
    def __init__(self, tmp_path):
        self.brain = FakeBrain()
        self.settings = FakeSettings(tmp_path)


class FakeRecorder:
    def __init__(self, canned_audio=b"\x01\x02"):
        self.canned_audio = canned_audio
        self.started = False
        self.saved = None

    def start(self):
        self.started = True

    def stop(self):
        return self.canned_audio

    def save_wav(self, path, audio_bytes):
        self.saved = (path, audio_bytes)


def test_submit_text_runs_through_the_brain(tmp_path):
    system = FakeSystem(tmp_path)
    app = OrbitDesktopApp(system)

    reply = app.submit_text("open chrome")

    assert reply == "handled: open chrome"
    assert system.brain.text_calls == ["open chrome"]


def test_submit_text_ignores_blank_input(tmp_path):
    system = FakeSystem(tmp_path)
    app = OrbitDesktopApp(system)

    assert app.submit_text("   ") == ""
    assert system.brain.text_calls == []


def test_mic_hold_records_and_processes_voice(tmp_path):
    system = FakeSystem(tmp_path)
    recorder = FakeRecorder()
    app = OrbitDesktopApp(system, recorder=recorder)

    app.start_recording()
    assert recorder.started is True

    reply = app.stop_recording_and_process()

    assert reply == "handled voice"
    assert recorder.saved is not None
    assert system.brain.voice_calls == [str(system.settings.data_dir / "last_command.wav")]


def test_mic_hold_with_no_audio_gives_a_hint_instead_of_calling_the_brain(tmp_path):
    system = FakeSystem(tmp_path)
    recorder = FakeRecorder(canned_audio=b"")
    app = OrbitDesktopApp(system, recorder=recorder)

    app.start_recording()
    reply = app.stop_recording_and_process()

    assert "heard nothing" in reply
    assert system.brain.voice_calls == []


def test_stop_recording_without_recorder_is_a_noop(tmp_path):
    system = FakeSystem(tmp_path)
    app = OrbitDesktopApp(system, recorder=None)

    app.start_recording()  # must not raise
    assert app.stop_recording_and_process() == ""


def test_stop_delegates_to_brain(tmp_path):
    system = FakeSystem(tmp_path)
    app = OrbitDesktopApp(system)

    app.stop()

    assert system.brain.stopped is True
