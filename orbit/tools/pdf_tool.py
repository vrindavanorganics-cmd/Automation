"""Tool: read and summarize PDF documents."""
from __future__ import annotations

from typing import Optional

from orbit.files import fs_ops, pdf_ops
from orbit.tools.base import Tool, ToolResult


def _not_found_message(hint: str, folder_hint: Optional[str]) -> str:
    location = f"your {folder_hint} folder" if folder_hint else "your Downloads/Desktop/Documents folders"
    if not hint:
        return f"Couldn't find any PDF in {location}"
    return f"Couldn't find a PDF matching '{hint}' in {location}"


class PdfTool(Tool):
    name = "pdf"

    def do_read(self, path: str) -> ToolResult:
        result = pdf_ops.read_pdf(path)
        return ToolResult.ok(
            f"Read {result.page_count} page(s) from {path}",
            path=path,
            page_count=result.page_count,
            text=result.text,
        )

    def do_summarize(self, path: str, max_sentences: int = 5) -> ToolResult:
        summary = pdf_ops.summarize_pdf(path, max_sentences=max_sentences)
        return ToolResult.ok("Summarized document", path=path, summary=summary)

    def do_find_and_read(self, hint: str, folder_hint: Optional[str] = None) -> ToolResult:
        path = fs_ops.find_file_in_common_locations(hint, folder_hint, extensions=(".pdf",))
        if not path:
            return ToolResult.fail(_not_found_message(hint, folder_hint))
        result = pdf_ops.read_pdf(path)
        return ToolResult.ok(
            f"Read {result.page_count} page(s) from '{path.name}'",
            path=str(path),
            page_count=result.page_count,
            text=result.text,
        )

    def do_find_and_summarize(
        self, hint: str, folder_hint: Optional[str] = None, max_sentences: int = 5
    ) -> ToolResult:
        path = fs_ops.find_file_in_common_locations(hint, folder_hint, extensions=(".pdf",))
        if not path:
            return ToolResult.fail(_not_found_message(hint, folder_hint))
        summary = pdf_ops.summarize_pdf(path, max_sentences=max_sentences)
        return ToolResult.ok(f"Summarized '{path.name}'", path=str(path), summary=summary)
