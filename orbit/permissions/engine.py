"""Permission levels and confirmation gating for ORBIT actions.

SAFE actions execute immediately. SENSITIVE actions must be confirmed by the
user before they run — no exceptions, no auto-approval for "bulk" or
"repeated" actions.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional


class PermissionLevel(str, Enum):
    SAFE = "safe"
    SENSITIVE = "sensitive"


# Canonical classification of built-in action names. Tools register their own
# action names here (or pass an explicit level) — this table is the default
# for anything not otherwise specified.
SENSITIVE_ACTIONS = {
    "send_email",
    "send_whatsapp_message",
    "delete_file",
    "delete_folder",
    "make_purchase",
    "submit_form",
    "change_password",
    "change_account_settings",
    "publish",
    "bulk_action",
    "financial_action",
    "send_message",
}

SAFE_ACTIONS = {
    "open_app",
    "close_app",
    "search",
    "read_file",
    "read_page",
    "create_draft",
    "create_file",
    "create_folder",
    "organize_files",
    "take_screenshot",
    "extract_text",
    "summarize",
    "navigate_browser",
}


class PermissionDenied(Exception):
    """Raised when a sensitive action is not confirmed by the user."""


@dataclass
class ConfirmationRequest:
    action: str
    description: str
    details: dict


ConfirmCallback = Callable[[ConfirmationRequest], bool]


def _default_confirm_callback(request: ConfirmationRequest) -> bool:
    """Fallback confirmation used when no UI/voice confirm handler is wired.

    Denies by default — ORBIT must never silently perform sensitive actions.
    Callers (CLI, UI, voice loop) should always supply a real callback.
    """
    return False


class PermissionEngine:
    """Classifies actions and gates sensitive ones behind explicit confirmation."""

    def __init__(self, confirm_callback: Optional[ConfirmCallback] = None, require_confirmation: bool = True):
        self._confirm_callback = confirm_callback or _default_confirm_callback
        self.require_confirmation = require_confirmation
        self._explicit_levels: dict[str, PermissionLevel] = {}

    def set_level(self, action: str, level: PermissionLevel) -> None:
        self._explicit_levels[action] = level

    def classify(self, action: str) -> PermissionLevel:
        if action in self._explicit_levels:
            return self._explicit_levels[action]
        if action in SENSITIVE_ACTIONS:
            return PermissionLevel.SENSITIVE
        if action in SAFE_ACTIONS:
            return PermissionLevel.SAFE
        # Unknown actions default to SENSITIVE — safest default.
        return PermissionLevel.SENSITIVE

    def authorize(
        self, action: str, description: str, details: Optional[dict] = None, force_sensitive: bool = False
    ) -> bool:
        """Returns True if the action is allowed to proceed.

        `force_sensitive` lets a caller (a plan step or skill step marked
        `requires_approval=True`) demand confirmation even for an action
        that defaults to SAFE — e.g. a skill author decided a particular
        step in *their* workflow needs a checkpoint.
        """
        level = PermissionLevel.SENSITIVE if force_sensitive else self.classify(action)
        if level == PermissionLevel.SAFE:
            return True
        if not self.require_confirmation:
            return True
        request = ConfirmationRequest(action=action, description=description, details=details or {})
        return bool(self._confirm_callback(request))

    def require(
        self, action: str, description: str, details: Optional[dict] = None, force_sensitive: bool = False
    ) -> None:
        if not self.authorize(action, description, details, force_sensitive=force_sensitive):
            raise PermissionDenied(f"Action '{action}' was not confirmed: {description}")
