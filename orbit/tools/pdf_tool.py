"""Tool: read and summarize PDF documents."""
from __future__ import annotations

from orbit.files import pdf_ops
from orbit.tools.base import Tool, ToolResult


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
