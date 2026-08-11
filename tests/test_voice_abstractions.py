from orbit.voice.hotkey import SimulatedHotkeyListener
from orbit.voice.recorder import SimulatedAudioRecorder
from orbit.voice.vad import SimpleEnergyVAD
import array


def test_simulated_hotkey_trigger_calls_callbacks():
    calls = []
    listener = SimulatedHotkeyListener("ctrl+shift+space", on_press=lambda: calls.append("press"), on_release=lambda: calls.append("release"))
    listener.start()
    listener.trigger()
    assert calls == ["press", "release"]
    assert listener.trigger_count == 1


def test_simulated_audio_recorder_returns_canned_audio():
    recorder = SimulatedAudioRecorder(canned_audio=b"\x01\x02")
    recorder.start()
    assert recorder.recording is True
    audio = recorder.stop()
    assert audio == b"\x01\x02"
    assert recorder.recording is False


def _tone(amplitude: int, n: int = 100) -> bytes:
    return array.array("h", [amplitude] * n).tobytes()


def test_simple_energy_vad_detects_loud_vs_silence():
    vad = SimpleEnergyVAD(threshold=500)
    assert vad.is_speech(_tone(3000)) is True
    assert vad.is_speech(_tone(10)) is False
    assert vad.is_speech(b"") is False
