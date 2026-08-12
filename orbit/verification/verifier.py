"""Verification framework: never assume an action succeeded.

Every tool execution goes through: PLAN -> EXECUTE -> VERIFY -> RESULT.
A ToolResult without a matching VerificationResult is considered unverified,
and the agent must report it as such rather than claiming success.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional


@dataclass
class VerificationResult:
    verified: bool
    message: str
    evidence: dict = field(default_factory=dict)

    @staticmethod
    def ok(message: str, **evidence: Any) -> "VerificationResult":
        return VerificationResult(True, message, evidence)

    @staticmethod
    def fail(message: str, **evidence: Any) -> "VerificationResult":
        return VerificationResult(False, message, evidence)


class Verifier:
    """Base class for a single verification check."""

    name = "base"

    def check(self, context: dict) -> VerificationResult:  # pragma: no cover - abstract
        raise NotImplementedError


class FileExistsVerifier(Verifier):
    name = "file_exists"

    def __init__(self, path_key: str = "path"):
        self.path_key = path_key

    def check(self, context: dict) -> VerificationResult:
        path = context.get(self.path_key)
        if not path:
            return VerificationResult.fail(f"No '{self.path_key}' provided to verify")
        p = Path(path)
        if p.exists():
            return VerificationResult.ok(f"File exists: {p}", path=str(p), size=p.stat().st_size)
        return VerificationResult.fail(f"File does not exist: {p}", path=str(p))


class FileContentChangedVerifier(Verifier):
    name = "file_content_changed"

    def check(self, context: dict) -> VerificationResult:
        before = context.get("before_hash")
        after = context.get("after_hash")
        if before is None or after is None:
            return VerificationResult.fail("Missing before/after hash to compare")
        if before != after:
            return VerificationResult.ok("File content changed as expected")
        return VerificationResult.fail("File content is unchanged")


class TextPresentVerifier(Verifier):
    """Verifies that expected text is present in a haystack (e.g. page content)."""

    name = "text_present"

    def check(self, context: dict) -> VerificationResult:
        haystack = context.get("haystack", "")
        needle = context.get("needle", "")
        if not needle:
            return VerificationResult.fail("No expected text provided")
        if needle.lower() in haystack.lower():
            return VerificationResult.ok(f"Found expected text: {needle!r}")
        return VerificationResult.fail(f"Expected text not found: {needle!r}")


class WindowOpenVerifier(Verifier):
    """Verifies an application window is present, using a WindowsController snapshot."""

    name = "window_open"

    def check(self, context: dict) -> VerificationResult:
        windows = context.get("windows", [])
        app_name = context.get("app_name", "")
        matches = [w for w in windows if app_name.lower() in w.lower()]
        if matches:
            return VerificationResult.ok(f"Window found for '{app_name}'", matches=matches)
        return VerificationResult.fail(f"No window found for '{app_name}'", windows=windows)


class CallableVerifier(Verifier):
    """Wraps an arbitrary function(context) -> VerificationResult for custom checks."""

    name = "callable"

    def __init__(self, fn: Callable[[dict], VerificationResult], name: Optional[str] = None):
        self._fn = fn
        if name:
            self.name = name

    def check(self, context: dict) -> VerificationResult:
        return self._fn(context)


def verify(verifier: Verifier, context: dict) -> VerificationResult:
    try:
        return verifier.check(context)
    except Exception as exc:  # verification itself must never crash the agent
        return VerificationResult.fail(f"Verification raised an error: {exc}")
