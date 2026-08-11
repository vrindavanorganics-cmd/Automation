"""Email sender abstraction — the actual "click send" step.

MockEmailSender: used for tests/dev; marks a draft sent without touching a
real mailbox.

BrowserGmailSender: drives Gmail's web UI via the BrowserController to
compose and send. Requires the user to already be logged into Gmail in the
automated browser profile on their Windows PC — this cannot be logged in or
tested from this browser workspace. Every method here is
LOCAL WINDOWS TEST NEEDED.
"""
from __future__ import annotations

from orbit.browser.playwright_controller import BrowserController
from orbit.email.models import EmailDraft


class EmailSender:
    def send(self, draft: EmailDraft) -> bool:
        raise NotImplementedError


class MockEmailSender(EmailSender):
    """Marks drafts as sent without any network/browser activity."""

    def __init__(self) -> None:
        self.sent: list[EmailDraft] = []

    def send(self, draft: EmailDraft) -> bool:
        self.sent.append(draft)
        return True


class BrowserGmailSender(EmailSender):
    """Composes and sends via https://mail.google.com using an already
    authenticated browser session. NOT exercised in this workspace — no
    Gmail login is available here. Requires local Windows testing with a
    real, logged-in Google account in ORBIT's browser profile.
    """

    COMPOSE_BUTTON = "div[role='button'][gh='cm']"
    TO_FIELD = "textarea[name='to']"
    SUBJECT_FIELD = "input[name='subjectbox']"
    BODY_FIELD = "div[aria-label='Message Body']"
    SEND_BUTTON = "div[role='button'][data-tooltip^='Send']"

    def __init__(self, browser: BrowserController):
        self.browser = browser

    def send(self, draft: EmailDraft) -> bool:
        self.browser.goto("https://mail.google.com/mail/u/0/#inbox")
        self.browser.click(self.COMPOSE_BUTTON)
        self.browser.type_text(self.TO_FIELD, draft.to)
        self.browser.type_text(self.SUBJECT_FIELD, draft.subject)
        self.browser.type_text(self.BODY_FIELD, draft.body)
        # Attachments would use the paperclip input[type=file] + set_input_files,
        # omitted here pending local Windows verification of Gmail's current DOM.
        self.browser.click(self.SEND_BUTTON)
        return True
