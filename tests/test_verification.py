from orbit.verification.verifier import (
    FileExistsVerifier,
    TextPresentVerifier,
    WindowOpenVerifier,
    verify,
)


def test_file_exists_verifier_pass(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hi")
    result = verify(FileExistsVerifier(), {"path": str(f)})
    assert result.verified is True


def test_file_exists_verifier_fail(tmp_path):
    result = verify(FileExistsVerifier(), {"path": str(tmp_path / "missing.txt")})
    assert result.verified is False


def test_text_present_verifier():
    result = verify(TextPresentVerifier(), {"haystack": "Hello ORBIT world", "needle": "orbit"})
    assert result.verified is True
    result = verify(TextPresentVerifier(), {"haystack": "Hello world", "needle": "orbit"})
    assert result.verified is False


def test_window_open_verifier():
    result = verify(WindowOpenVerifier(), {"windows": ["Google Chrome - New Tab"], "app_name": "Chrome"})
    assert result.verified is True
    result = verify(WindowOpenVerifier(), {"windows": [], "app_name": "Chrome"})
    assert result.verified is False


def test_verify_never_raises():
    class BrokenVerifier:
        name = "broken"

        def check(self, context):
            raise ValueError("boom")

    result = verify(BrokenVerifier(), {})
    assert result.verified is False
    assert "boom" in result.message
