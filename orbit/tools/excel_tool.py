"""Tool: create and manipulate Excel spreadsheets."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from orbit.files import excel_ops
from orbit.tools.base import Tool, ToolResult


class ExcelTool(Tool):
    name = "excel"

    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir

    def _resolve(self, path: str) -> str:
        p = Path(path)
        return str(p if p.is_absolute() else Path(self.base_dir) / p)

    def do_create(self, path: str = "output.xlsx", rows: list[list[Any]] | None = None, records: list[dict] | None = None) -> ToolResult:
        resolved = self._resolve(path)
        if records is not None:
            created = excel_ops.create_workbook_from_records(resolved, records)
        else:
            created = excel_ops.create_workbook(resolved, rows or [])
        return ToolResult.ok(f"Created Excel file '{created}'", path=str(created))

    def do_read(self, path: str, sheet_name: str | None = None) -> ToolResult:
        rows = excel_ops.read_workbook(path, sheet_name)
        return ToolResult.ok(f"Read {len(rows)} row(s) from {path}", path=path, rows=rows)

    def do_append_row(self, path: str, row: list[Any], sheet_name: str | None = None) -> ToolResult:
        excel_ops.append_row(path, row, sheet_name)
        return ToolResult.ok(f"Appended row to {path}", path=path)

    def do_update_cell(self, path: str, cell: str, value: Any, sheet_name: str | None = None) -> ToolResult:
        excel_ops.update_cell(path, cell, value, sheet_name)
        return ToolResult.ok(f"Updated {cell} in {path}", path=path, cell=cell)
