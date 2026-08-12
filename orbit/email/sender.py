"""Email sender abstraction — the actual Gmail interaction.

MockEmailSender: used for tests/dev; marks a draft sent without touching a
real mailbox. `draft()` is a local-only no-op (returns False) so callers can
tell that nothing actually happened in a real mailbox.

BrowserGmailSender: drives Gmail's web UI through the same shared browser
session as the `browser` tool (so a login persists across commands within a
run). Requires the user to already be logged into Gmail in that browser
profile — ORBIT does not automate login/2FA. Selectors target Gmail's
classic, long-stable DOM attributes (gh='cm', name='to', etc.), but Gmail's
markup is not a public API and can change; this is the one part of ORBIT
that could need a selector update after a Gmail redesign. NOT exercised in
this workspace — no Gmail login is available here. LOCAL WINDOWS TEST NEEDED.
"""
from __future__ import annotations

from typing import Optional

from orbit.email.models import EmailDraft


class EmailSender:
    def send(self, draft: EmailDraft) -> bool:
        raise NotImplementedError

    def draft(self, draft: EmailDraft) -> bool:
        """Best-effort: open/create this draft in the real mail client.
        Default is a local-only no-op (returns False) -- override to
        actually reach a mailbox.
        """
        return False


class MockEmailSender(EmailSender):
    """Marks drafts as sent without any network/browser activity."""

    def __init__(self) -> None:
        self.sent: list[EmailDraft] = []

    def send(self, draft: EmailDraft) -> bool:
        self.sent.append(draft)
        return True


class BrowserGmailSender(EmailSender):
    """Composes, drafts, and sends via https://mail.google.com using the
    project's shared browser session (the same one the `browser` tool
    uses), so a Gmail login made in one ORBIT command is still active for
    the next. Tracks the most recently drafted compose window so that
    "draft it" followed later by "send it" in the same run reuses the same
    open compose box instead of re-typing everything.
    """

    COMPOSE_BUTTON = "div[role='button'][gh='cm']"
    TO_FIELD = "textarea[name='to']"
    SUBJECT_FIELD = "input[name='subjectbox']"
    BODY_FIELD = "div[aria-label='Message Body']"
    SEND_BUTTON = "div[role='button'][data-tooltip^='Send']"

    def __init__(self, browser_tool):
        self.browser_tool = browser_tool
        self._open_compose_draft_id: Optional[str] = None

    def _controller(self):
        return self.browser_tool.get_controller()

    def _compose(self, draft: EmailDraft) -> None:
        bc = self._controller()
        bc.goto("https://mail.google.com/mail/u/0/#inbox")
        bc.click(self.COMPOSE_BUTTON)
        bc.type_text(self.TO_FIELD, draft.to)
        bc.type_text(self.SUBJECT_FIELD, draft.subject)
        bc.type_text(self.BODY_FIELD, draft.body)
        # Attachments would use the paperclip input[type=file] + set_input_files,
        # omitted here pending local Windows verification of Gmail's current DOM.

    def draft(self, draft: EmailDraft) -> bool:
        """Opens a real Gmail compose window and fills it in, leaving it
        open (Gmail auto-saves an open, filled-in compose as a draft).
        """
        self._compose(draft)
        self._open_compose_draft_id = draft.id
        return True

    def send(self, draft: EmailDraft) -> bool:
        bc = self._controller()
        if self._open_compose_draft_id != draft.id:
            # No open compose window for this draft (e.g. ORBIT was
            # restarted, or send was called without draft() first) --
            # compose fresh instead of assuming prior state.
            self._compose(draft)
        bc.click(self.SEND_BUTTON)
        self._open_compose_draft_id = None
        return True
