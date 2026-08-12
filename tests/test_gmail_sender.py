"""Tests BrowserGmailSender's draft/send flow against a fake browser
controller (no real Gmail/network involved) -- verifies the *sequencing*
logic (compose once, reuse the open compose for send) that a real
Playwright-driven test can't easily assert on.
"""
from orbit.email.models import EmailDraft
from orbit.email.sender import BrowserGmailSender


class FakeController:
    def __init__(self):
        self.calls: list[tuple] = []

    def goto(self, url):
        self.calls.append(("goto", url))

    def click(self, selector):
        self.calls.append(("click", selector))

    def type_text(self, selector, text):
        self.calls.append(("type_text", selector, text))


class FakeBrowserTool:
    def __init__(self):
        self.controller = FakeController()

    def get_controller(self):
        return self.controller


def test_draft_opens_compose_and_fills_fields_without_sending():
    browser_tool = FakeBrowserTool()
    sender = BrowserGmailSender(browser_tool)
    draft = EmailDraft(to="buyer@example.com", subject="Quotation", body="Hello")

    ok = sender.draft(draft)

    assert ok is True
    actions = [c[0] for c in browser_tool.controller.calls]
    assert actions == ["goto", "click", "type_text", "type_text", "type_text"]
    assert ("click", BrowserGmailSender.SEND_BUTTON) not in browser_tool.controller.calls


def test_send_after_draft_reuses_open_compose_without_recomposing():
    browser_tool = FakeBrowserTool()
    sender = BrowserGmailSender(browser_tool)
    draft = EmailDraft(to="buyer@example.com", subject="Quotation", body="Hello")

    sender.draft(draft)
    browser_tool.controller.calls.clear()
    ok = sender.send(draft)

    assert ok is True
    # Only the Send click -- no re-navigating/re-filling the same compose.
    assert browser_tool.controller.calls == [("click", BrowserGmailSender.SEND_BUTTON)]


def test_send_without_prior_draft_composes_fresh_then_sends():
    browser_tool = FakeBrowserTool()
    sender = BrowserGmailSender(browser_tool)
    draft = EmailDraft(to="buyer@example.com", subject="Quotation", body="Hello")

    ok = sender.send(draft)

    assert ok is True
    actions = [c[0] for c in browser_tool.controller.calls]
    assert actions == ["goto", "click", "type_text", "type_text", "type_text", "click"]


def test_send_for_a_different_draft_after_composing_recomposes():
    browser_tool = FakeBrowserTool()
    sender = BrowserGmailSender(browser_tool)
    first = EmailDraft(to="a@example.com", subject="A", body="a")
    second = EmailDraft(to="b@example.com", subject="B", body="b")

    sender.draft(first)
    browser_tool.controller.calls.clear()
    sender.send(second)

    actions = [c[0] for c in browser_tool.controller.calls]
    assert actions == ["goto", "click", "type_text", "type_text", "type_text", "click"]
