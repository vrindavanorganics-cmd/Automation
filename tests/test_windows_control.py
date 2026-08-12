from orbit.windows.app_registry import AppRegistry
from orbit.windows.control import SimulatedController, get_controller


def test_simulated_launch_and_list():
    controller = SimulatedController()
    assert controller.launch_app("chrome.exe") is True
    assert "chrome.exe" in controller.list_windows()


def test_simulated_close():
    controller = SimulatedController()
    controller.launch_app("chrome.exe")
    assert controller.close_app("chrome") is True
    assert controller.list_windows() == []


def test_simulated_close_missing_returns_false():
    controller = SimulatedController()
    assert controller.close_app("nonexistent") is False


def test_simulated_clipboard():
    controller = SimulatedController()
    controller.set_clipboard("hello")
    assert controller.get_clipboard() == "hello"


def test_simulated_screenshot(tmp_path):
    controller = SimulatedController()
    path = str(tmp_path / "shot.png")
    assert controller.screenshot(path) is True
    assert (tmp_path / "shot.png").exists()


def test_action_log_records_everything():
    controller = SimulatedController()
    controller.launch_app("chrome.exe")
    controller.key_press("ctrl+t")
    assert len(controller.action_log) == 2


def test_get_controller_forces_simulated():
    controller = get_controller(force_simulated=True)
    assert controller.backend_name == "simulated"


def test_app_registry_resolve_by_alias():
    registry = AppRegistry()
    entry = registry.resolve("chrome")
    assert entry is not None
    assert entry.name == "Google Chrome"


def test_app_registry_resolve_unknown_returns_none():
    registry = AppRegistry()
    assert registry.resolve("totally unknown app xyz") is None


def test_app_registry_resolve_empty_string_returns_none():
    # Regression: "" is a substring of every app name, so an unresolved
    # entity (e.g. "open edge" before Edge was registered) must not
    # silently fall through to matching whichever app is registered first.
    registry = AppRegistry()
    assert registry.resolve("") is None
    assert registry.resolve("   ") is None


def test_app_registry_resolve_edge_by_alias():
    registry = AppRegistry()
    entry = registry.resolve("edge")
    assert entry is not None
    assert entry.name == "Microsoft Edge"
