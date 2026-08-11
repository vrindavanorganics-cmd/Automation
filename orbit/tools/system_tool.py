"""Tool: system-level plan steps (stop, clarification, summaries) that don't
belong to a specific domain tool. Approval itself is handled by the
permission engine before a step runs — `ask_approval` here is just the
user-facing checkpoint step in a multi-step plan.
"""
from __future__ import annotations

from orbit.tools.base import Tool, ToolResult


class SystemTool(Tool):
    name = "system"
    sensitive_actions: set[str] = set()

    def do_stop(self) -> ToolResult:
        return ToolResult.ok("Stopped")

    def do_ask_clarification(self, heard: str = "") -> ToolResult:
        return ToolResult.ok(f"I didn't understand that command: '{heard}'. Could you rephrase?", heard=heard)

    def do_show_summary(self, **details) -> ToolResult:
        return ToolResult.ok("Summary shown", **details)

    def do_ask_approval(self, **details) -> ToolResult:
        return ToolResult.ok("Approval requested", **details)
