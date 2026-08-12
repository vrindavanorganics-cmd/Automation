from orbit.files import fs_ops
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


def test_find_and_summarize_locates_file_by_hint(tmp_path, monkeypatch, sample_pdf):
    monkeypatch.setattr(fs_ops.Path, "home", classmethod(lambda cls: tmp_path))
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    target = downloads / "Ekagya_Camscanner.pdf"
    target.write_bytes(sample_pdf.read_bytes())

    tool = PdfTool()
    result = tool.run("find_and_summarize", {"hint": "camscanner"})

    assert result.success
    assert result.data["path"] == str(target)
    assert len(result.data["summary"]) > 0


def test_find_and_read_no_match_fails_clearly(tmp_path, monkeypatch):
    monkeypatch.setattr(fs_ops.Path, "home", classmethod(lambda cls: tmp_path))
    (tmp_path / "Downloads").mkdir()

    tool = PdfTool()
    result = tool.run("find_and_read", {"hint": "nonexistent"})

    assert not result.success
    assert "Couldn't find" in result.message
