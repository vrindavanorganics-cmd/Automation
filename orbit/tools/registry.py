"""Tool registry: name -> Tool instance lookup used by the agent brain."""
from __future__ import annotations

from orbit.tools.base import Tool, ToolResult


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list(self) -> list[str]:
        return sorted(self._tools.keys())

    def run(self, tool_name: str, action: str, params: dict) -> ToolResult:
        tool = self.get(tool_name)
        if tool is None:
            return ToolResult.fail(f"Unknown tool '{tool_name}'")
        return tool.run(action, params)
