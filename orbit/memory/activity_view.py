"""Formats activity log entries for display (CLI/UI), matching the
lightweight checklist style from the ORBIT spec:

    ✓ Opened Gmail
    ✓ Found contact
    ✓ Attached quotation
    ✓ Draft created
    ✓ User approved
    ✓ Email sent
"""
from __future__ import annotations

import datetime as _dt

from orbit.memory.store import ActivityRecord


def format_activity_record(record: ActivityRecord) -> str:
    ts = _dt.datetime.fromtimestamp(record.timestamp).strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"[{ts}] {record.command}  ({record.status})"]
    for action in record.actions:
        mark = "✓" if record.status == "success" else "✗"
        lines.append(f"  {mark} {action}")
    if record.result:
        lines.append(f"  -> {record.result}")
    return "\n".join(lines)


def format_activity_list(records: list[ActivityRecord]) -> str:
    return "\n\n".join(format_activity_record(r) for r in records)
