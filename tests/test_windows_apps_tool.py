from orbit.tools.windows_apps import WindowsAppsTool
from orbit.windows.app_registry import AppEntry, AppRegistry
from orbit.windows.control import SimulatedController


def test_open_app_prefers_resolved_path_over_bare_executable():
    # Regression: launching by bare executable name (e.g. "chrome.exe")
    # relies on Windows finding it via PATH, which often silently fails
    # even when Popen() itself doesn't raise. The full resolved path found
    # by AppRegistry.detect_installed() must be used when available.
    registry = AppRegistry(
        apps=[
            AppEntry(
                name="Google Chrome",
                executable="chrome.exe",
                aliases=["chrome"],
                installed=True,
                resolved_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            )
        ]
    )
    controller = SimulatedController()
    tool = WindowsAppsTool(controller, registry)

    result = tool.run("open_app", {"app": "chrome"})

    assert result.success
    assert controller.list_windows() == [r"C:\Program Files\Google\Chrome\Application\chrome.exe"]


def test_open_app_falls_back_to_bare_executable_when_unresolved():
    registry = AppRegistry(apps=[AppEntry(name="Notion", executable="Notion.exe", aliases=["notion"])])
    controller = SimulatedController()
    tool = WindowsAppsTool(controller, registry)

    result = tool.run("open_app", {"app": "notion"})

    assert result.success
    assert "Notion.exe" in controller.list_windows()


def test_open_app_reports_not_installed(monkeypatch):
    registry = AppRegistry(apps=[AppEntry(name="Notion", executable="Notion.exe", aliases=["notion"], installed=False)])
    controller = SimulatedController()
    monkeypatch.setattr(controller, "launch_app", lambda *a, **k: False)
    tool = WindowsAppsTool(controller, registry)

    result = tool.run("open_app", {"app": "notion"})

    assert not result.success
    assert "does not appear to be installed" in result.message


def test_open_app_unresolvable_name_does_not_silently_launch_wrong_app():
    # Regression: an empty/unresolved app entity used to silently resolve
    # to whichever app was registered first via AppRegistry's substring
    # fallback, so "open edge" (unrecognized) launched Chrome instead.
    registry = AppRegistry(apps=[AppEntry(name="Google Chrome", executable="chrome.exe", aliases=["chrome"])])
    controller = SimulatedController()
    tool = WindowsAppsTool(controller, registry)

    result = tool.run("open_app", {"app": ""})

    assert not result.success
    assert controller.list_windows() == []
