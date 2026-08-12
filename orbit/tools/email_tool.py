"""Tool: draft, attach, send, and verify emails.

Drafting is SAFE and happens immediately. Sending is SENSITIVE and must
always go through the permission engine's confirmation gate before this
tool's do_send_email is even called (the agent brain enforces that).
"""
from __future__ import annotations

import time
from typing import Optional

from orbit.email.models import EmailDraft
from orbit.email.sender import EmailSender
from orbit.email.store import DraftStore
from orbit.tools.base import Tool, ToolResult


class EmailTool(Tool):
    name = "email"
    sensitive_actions = {"send_email", "send_bulk"}

    def __init__(self, sender: EmailSender, store: Optional[DraftStore] = None):
        self.sender = sender
        self.store = store or DraftStore()

    def do_draft(self, to: str, subject: str, body: str, attachments: Optional[list[str]] = None) -> ToolResult:
        draft = EmailDraft(to=to, subject=subject, body=body, attachments=attachments or [])
        self.store.add(draft)

        live_ok = False
        live_error: Optional[str] = None
        try:
            live_ok = self.sender.draft(draft)
        except Exception as exc:  # a live Gmail/browser hiccup shouldn't lose the local draft
            live_error = str(exc)

        if live_ok:
            message = f"Drafted email to {to} (opened in Gmail)"
        elif live_error:
            message = f"Drafted email to {to} locally -- could not open it in Gmail: {live_error}"
        else:
            message = f"Drafted email to {to} (local draft only -- no live mail client connected)"

        return ToolResult.ok(message, draft_id=draft.id, draft=draft.to_dict(), live_gmail=live_ok)

    def do_draft_bulk(self, companies: list[str], template: str, attachment: Optional[str] = None) -> ToolResult:
        drafts = []
        for company in companies:
            body = template.replace("{company}", company)
            draft = EmailDraft(to=f"contact@{company.lower().replace(' ', '')}.example", subject=f"Quotation for {company}", body=body, attachments=[attachment] if attachment else [])
            self.store.add(draft)
            drafts.append(draft.to_dict())
        return ToolResult.ok(f"Drafted {len(drafts)} email(s)", drafts=drafts)

    def do_attach(self, draft_id: str, attachment: str) -> ToolResult:
        draft = self.store.get(draft_id)
        if not draft:
            return ToolResult.fail(f"No draft with id '{draft_id}'")
        draft.attachments.append(attachment)
        return ToolResult.ok(f"Attached '{attachment}' to draft {draft_id}", draft_id=draft_id)

    def do_list_drafts(self, status: Optional[str] = None) -> ToolResult:
        drafts = self.store.list(status)
        return ToolResult.ok(f"{len(drafts)} draft(s)", drafts=[d.to_dict() for d in drafts])

    def _resolve_draft(self, draft_id: Optional[str]) -> Optional[EmailDraft]:
        """Resolves an explicit draft_id, or falls back to the most recently
        created pending draft — so a bare "send it" / "don't send it"
        naturally refers to whatever ORBIT just drafted.
        """
        if draft_id:
            return self.store.get(draft_id)
        pending = self.store.list("draft")
        if not pending:
            return None
        return max(pending, key=lambda d: d.created_at)

    def do_send_email(self, draft_id: Optional[str] = None) -> ToolResult:
        draft = self._resolve_draft(draft_id)
        if not draft:
            return ToolResult.fail("No pending draft to send")
        if draft.status != "draft":
            return ToolResult.fail(f"Draft {draft.id} is not pending (status={draft.status})")
        ok = self.sender.send(draft)
        if ok:
            self.store.update_status(draft.id, "sent", sent_at=time.time())
            return ToolResult.ok(f"Sent email to {draft.to}", draft_id=draft.id, to=draft.to)
        self.store.update_status(draft.id, "failed")
        return ToolResult.fail(f"Failed to send email to {draft.to}", draft_id=draft.id)

    def do_send_bulk(self, companies: Optional[list[str]] = None) -> ToolResult:
        pending = [d for d in self.store.list("draft") if companies is None or d.to in companies]
        sent, failed = [], []
        for draft in pending:
            if self.sender.send(draft):
                self.store.update_status(draft.id, "sent", sent_at=time.time())
                sent.append(draft.to)
            else:
                self.store.update_status(draft.id, "failed")
                failed.append(draft.to)
        return ToolResult.ok(f"Sent {len(sent)}/{len(pending)} email(s)", sent=sent, failed=failed)

    def do_cancel_send(self, draft_id: Optional[str] = None) -> ToolResult:
        draft = self._resolve_draft(draft_id)
        if not draft:
            return ToolResult.fail("No pending draft to cancel")
        self.store.update_status(draft.id, "cancelled")
        return ToolResult.ok(f"Cancelled draft {draft.id}", draft_id=draft.id)

    def do_verify_sent(self, companies: Optional[list[str]] = None) -> ToolResult:
        sent = [d for d in self.store.list("sent") if companies is None or d.to in companies]
        return ToolResult.ok(f"{len(sent)} email(s) confirmed sent", sent=[d.to_dict() for d in sent])

    def do_read(self) -> ToolResult:
        # Reading a real inbox requires a live, logged-in browser session on
        # the user's Windows PC (Gmail/Outlook web). Not available here.
        return ToolResult.fail(
            "Reading a live inbox requires local Windows testing with a logged-in email account"
        )
