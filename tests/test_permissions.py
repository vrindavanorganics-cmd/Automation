import pytest

from orbit.permissions.engine import PermissionDenied, PermissionEngine, PermissionLevel


def test_safe_action_never_asks():
    calls = []
    engine = PermissionEngine(confirm_callback=lambda r: calls.append(r) or True)
    assert engine.authorize("open_app", "Open Chrome") is True
    assert calls == []


def test_sensitive_action_requires_confirmation_denied_by_default():
    engine = PermissionEngine()  # no callback -> defaults to deny
    assert engine.authorize("send_email", "Send an email") is False


def test_sensitive_action_confirmed():
    engine = PermissionEngine(confirm_callback=lambda r: True)
    assert engine.authorize("send_email", "Send an email") is True


def test_unknown_action_defaults_to_sensitive():
    engine = PermissionEngine(confirm_callback=lambda r: False)
    assert engine.classify("some_new_action") == PermissionLevel.SENSITIVE


def test_require_raises_when_denied():
    engine = PermissionEngine(confirm_callback=lambda r: False)
    with pytest.raises(PermissionDenied):
        engine.require("delete_file", "Delete report.xlsx")


def test_require_confirmation_false_bypasses_confirm():
    engine = PermissionEngine(confirm_callback=lambda r: False, require_confirmation=False)
    assert engine.authorize("send_email", "Send") is True


def test_explicit_level_override():
    engine = PermissionEngine(confirm_callback=lambda r: False)
    engine.set_level("custom_read", PermissionLevel.SAFE)
    assert engine.authorize("custom_read", "Read something") is True
