"""In-memory (per-session) draft store. Drafts are ephemeral working state,
not long-term memory — completed sends are recorded in activity history
(orbit.memory.store) instead.
"""
from __future__ import annotations

from orbit.email.models import EmailDraft


class DraftStore:
    def __init__(self) -> None:
        self._drafts: dict[str, EmailDraft] = {}

    def add(self, draft: EmailDraft) -> EmailDraft:
        self._drafts[draft.id] = draft
        return draft

    def get(self, draft_id: str) -> EmailDraft | None:
        return self._drafts.get(draft_id)

    def list(self, status: str | None = None) -> list[EmailDraft]:
        drafts = list(self._drafts.values())
        if status:
            drafts = [d for d in drafts if d.status == status]
        return drafts

    def update_status(self, draft_id: str, status: str, sent_at: float | None = None) -> None:
        draft = self._drafts.get(draft_id)
        if draft:
            draft.status = status
            if sent_at is not None:
                draft.sent_at = sent_at

    def remove(self, draft_id: str) -> None:
        self._drafts.pop(draft_id, None)
