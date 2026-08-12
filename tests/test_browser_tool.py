import pytest

from orbit.tools.browser_tool import BrowserTool


@pytest.fixture
def html_page(tmp_path):
    html = "<html><head><title>Orbit Test Page</title></head><body><h1>Hello Orbit</h1><p>ORBIT browser control works.</p></body></html>"
    path = tmp_path / "page.html"
    path.write_text(html)
    return "file://" + str(path)


def test_browser_open_and_extract_text(html_page):
    tool = BrowserTool(headless=True)
    try:
        result = tool.run("open", {"url": html_page})
        assert result.success
        assert result.data["title"] == "Orbit Test Page"

        extracted = tool.run("extract_text", {})
        assert "ORBIT browser control works" in extracted.data["text"]
    finally:
        tool.shutdown()


def test_browser_screenshot(html_page, tmp_path):
    tool = BrowserTool(headless=True)
    try:
        tool.run("open", {"url": html_page})
        shot_path = str(tmp_path / "shot.png")
        result = tool.run("screenshot", {"path": shot_path})
        assert result.success
        assert (tmp_path / "shot.png").exists()
    finally:
        tool.shutdown()


def test_get_controller_shares_one_session(html_page):
    # Regression: BrowserGmailSender needs the *same* browser session as the
    # browser tool (so a Gmail login persists), not a second, separate one.
    tool = BrowserTool(headless=True)
    try:
        controller_a = tool.get_controller()
        tool.run("open", {"url": html_page})
        controller_b = tool.get_controller()
        assert controller_a is controller_b
    finally:
        tool.shutdown()


def test_persistent_profile_survives_across_sessions(tmp_path, html_page):
    profile_dir = tmp_path / "profile"
    tool = BrowserTool(headless=True, profile_dir=str(profile_dir))
    try:
        result = tool.run("open", {"url": html_page})
        assert result.success
    finally:
        tool.shutdown()

    assert profile_dir.is_dir()
    assert any(profile_dir.iterdir())  # Playwright wrote real profile state to disk
