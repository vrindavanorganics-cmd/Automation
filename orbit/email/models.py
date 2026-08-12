"""Email draft data model."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


@dataclass
class EmailDraft:
    to: str
    subject: str
    body: str
    attachments: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    status: str = "draft"  # draft | sent | cancelled | failed
    created_at: float = field(default_factory=time.time)
    sent_at: float | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "to": self.to,
            "subject": self.subject,
            "body": self.body,
            "attachments": self.attachments,
            "status": self.status,
            "created_at": self.created_at,
            "sent_at": self.sent_at,
        }
