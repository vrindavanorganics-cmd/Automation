"""Tool interface and result contract every ORBIT tool implements."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    success: bool
    message: str
    data: dict = field(default_factory=dict)

    @staticmethod
    def ok(message: str, **data: Any) -> "ToolResult":
        return ToolResult(True, message, data)

    @staticmethod
    def fail(message: str, **data: Any) -> "ToolResult":
        return ToolResult(False, message, data)


class Tool:
    """Base class for all ORBIT tools (windows_apps, files, pdf, excel,
    browser, email, skills, system...). Each tool declares which of its
    actions are sensitive via `sensitive_actions`.
    """

    name = "tool"
    sensitive_actions: set[str] = set()

    def run(self, action: str, params: dict) -> ToolResult:
        handler = getattr(self, f"do_{action}", None)
        if handler is None:
            return ToolResult.fail(f"Tool '{self.name}' has no action '{action}'")
        try:
            return handler(**params)
        except TypeError as exc:
            return ToolResult.fail(f"Invalid parameters for '{self.name}.{action}': {exc}")
        except Exception as exc:  # tools must never crash the agent loop
            return ToolResult.fail(f"'{self.name}.{action}' raised an error: {exc}")
