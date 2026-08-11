from orbit.tools.pdf_tool import PdfTool


def test_read_pdf_extracts_text(sample_pdf):
    tool = PdfTool()
    result = tool.run("read", {"path": str(sample_pdf)})
    assert result.success
    assert "Ekagya Exports" in result.data["text"]
    assert result.data["page_count"] == 1


def test_summarize_pdf_returns_nonempty_summary(sample_pdf):
    tool = PdfTool()
    result = tool.run("summarize", {"path": str(sample_pdf), "max_sentences": 2})
    assert result.success
    assert len(result.data["summary"]) > 0
