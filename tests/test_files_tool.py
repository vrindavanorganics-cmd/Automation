from orbit.files import excel_ops, fs_ops, pdf_ops


def test_create_and_read_file(tmp_path):
    created = fs_ops.create_file(tmp_path / "note.txt", "hello orbit")
    assert created.exists()
    assert fs_ops.read_text(created) == "hello orbit"


def test_create_folder(tmp_path):
    folder = fs_ops.create_folder(tmp_path / "Buyer Leads")
    assert folder.is_dir()


def test_move_and_copy(tmp_path):
    src = fs_ops.create_file(tmp_path / "a.txt", "x")
    dest_dir = tmp_path / "dest"
    copied = fs_ops.copy(src, dest_dir)
    assert copied.exists()
    assert src.exists()  # original still there after copy
    moved = fs_ops.move(copied, tmp_path / "moved")
    assert moved.exists()
    assert not copied.exists()


def test_organize_by_type(tmp_path):
    fs_ops.create_file(tmp_path / "report.pdf", "x")
    fs_ops.create_file(tmp_path / "data.xlsx", "x")
    fs_ops.create_file(tmp_path / "photo.png", "x")
    moved = fs_ops.organize_by_type(tmp_path)
    assert (tmp_path / "Documents" / "report.pdf").exists()
    assert (tmp_path / "Spreadsheets" / "data.xlsx").exists()
    assert (tmp_path / "Images" / "photo.png").exists()
    assert set(moved.keys()) == {"Documents", "Spreadsheets", "Images"}


def test_find_by_keyword(tmp_path):
    fs_ops.create_file(tmp_path / "Ekagya_Quotation.pdf", "x")
    fs_ops.create_file(tmp_path / "unrelated.txt", "x")
    matches = fs_ops.find_by_keyword(tmp_path, "ekagya")
    assert len(matches) == 1
    assert "Ekagya" in matches[0].name


def test_excel_create_and_read_records(tmp_path):
    path = tmp_path / "leads.xlsx"
    excel_ops.create_workbook_from_records(
        path, [{"Company": "Acme", "Email": "a@acme.com"}, {"Company": "Globex", "Email": "g@globex.com"}]
    )
    records = excel_ops.read_workbook_as_records(path)
    assert len(records) == 2
    assert records[0]["Company"] == "Acme"


def test_excel_append_and_update(tmp_path):
    path = tmp_path / "sheet.xlsx"
    excel_ops.create_workbook(path, [["Name", "Value"]])
    excel_ops.append_row(path, ["Row1", 1])
    excel_ops.update_cell(path, "B2", 42)
    rows = excel_ops.read_workbook(path)
    assert rows[1][1] == 42


def test_pdf_summarize_text_short_returns_all():
    text = "First sentence. Second sentence."
    summary = pdf_ops.summarize_text(text, max_sentences=5)
    assert "First sentence" in summary and "Second sentence" in summary


def test_pdf_summarize_text_long_picks_subset():
    text = " ".join([f"Sentence number {i} talks about business exports and quotations." for i in range(20)])
    summary = pdf_ops.summarize_text(text, max_sentences=3)
    assert len(pdf_ops._split_sentences(summary)) <= 3


def test_find_file_in_common_locations_by_hint(tmp_path, monkeypatch):
    monkeypatch.setattr(fs_ops.Path, "home", classmethod(lambda cls: tmp_path))
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    fs_ops.create_file(downloads / "unrelated.pdf", "x")
    fs_ops.create_file(downloads / "Ekagya_Camscanner_Quotation.pdf", "x")

    found = fs_ops.find_file_in_common_locations("camscanner", extensions=(".pdf",))

    assert found is not None
    assert found.name == "Ekagya_Camscanner_Quotation.pdf"


def test_find_file_in_common_locations_respects_folder_hint(tmp_path, monkeypatch):
    monkeypatch.setattr(fs_ops.Path, "home", classmethod(lambda cls: tmp_path))
    downloads = tmp_path / "Downloads"
    desktop = tmp_path / "Desktop"
    downloads.mkdir()
    desktop.mkdir()
    fs_ops.create_file(downloads / "invoice.pdf", "x")
    fs_ops.create_file(desktop / "invoice.pdf", "x")

    found = fs_ops.find_file_in_common_locations("invoice", folder_hint="desktop", extensions=(".pdf",))

    assert found is not None
    assert found.parent == desktop


def test_find_file_in_common_locations_empty_hint_returns_most_recent(tmp_path, monkeypatch):
    import time

    monkeypatch.setattr(fs_ops.Path, "home", classmethod(lambda cls: tmp_path))
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    older = fs_ops.create_file(downloads / "older.pdf", "x")
    time.sleep(0.01)
    newer = fs_ops.create_file(downloads / "newer.pdf", "x")

    found = fs_ops.find_file_in_common_locations("", extensions=(".pdf",))

    assert found == newer
    assert found != older


def test_find_file_in_common_locations_no_match_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(fs_ops.Path, "home", classmethod(lambda cls: tmp_path))
    (tmp_path / "Downloads").mkdir()

    assert fs_ops.find_file_in_common_locations("nonexistent", extensions=(".pdf",)) is None
