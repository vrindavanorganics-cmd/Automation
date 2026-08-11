from orbit.email.sender import MockEmailSender
from orbit.tools.email_tool import EmailTool


def test_draft_then_send_requires_explicit_call():
    sender = MockEmailSender()
    tool = EmailTool(sender=sender)

    draft_result = tool.run("draft", {"to": "buyer@example.com", "subject": "Quotation", "body": "Hello"})
    assert draft_result.success
    draft_id = draft_result.data["draft_id"]

    # Not sent yet.
    assert sender.sent == []

    send_result = tool.run("send_email", {"draft_id": draft_id})
    assert send_result.success
    assert len(sender.sent) == 1


def test_cancel_send_prevents_sending():
    sender = MockEmailSender()
    tool = EmailTool(sender=sender)
    draft_id = tool.run("draft", {"to": "x@example.com", "subject": "s", "body": "b"}).data["draft_id"]
    tool.run("cancel_send", {"draft_id": draft_id})
    result = tool.run("send_email", {"draft_id": draft_id})
    assert result.success is False


def test_draft_bulk_and_send_bulk():
    sender = MockEmailSender()
    tool = EmailTool(sender=sender)
    companies = ["Acme Foods", "Globex"]
    tool.run("draft_bulk", {"companies": companies, "template": "Hello {company}, please find our quotation."})
    listed = tool.run("list_drafts", {"status": "draft"})
    assert len(listed.data["drafts"]) == 2

    result = tool.run("send_bulk", {})
    assert result.success
    assert len(result.data["sent"]) == 2


def test_send_email_missing_draft_fails():
    tool = EmailTool(sender=MockEmailSender())
    result = tool.run("send_email", {"draft_id": "nonexistent"})
    assert result.success is False


def test_read_inbox_reports_local_windows_needed():
    tool = EmailTool(sender=MockEmailSender())
    result = tool.run("read", {})
    assert result.success is False
    assert "local Windows" in result.message
