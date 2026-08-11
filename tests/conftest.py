import pytest


@pytest.fixture
def sample_pdf(tmp_path):
    """Generates a real, readable PDF fixture (fpdf2 is a dev/test-only dependency)."""
    fpdf = pytest.importorskip("fpdf")
    pdf = fpdf.FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=14)
    text = (
        "Ekagya Exports quotation summary. We are pleased to offer premium Makhana "
        "and organic products for export. Please review pricing and terms. "
        "Contact Vrindavan Organics for further questions about this order. "
        "Delivery timelines depend on the shipping method chosen by the buyer."
    )
    pdf.multi_cell(0, 10, text)
    path = tmp_path / "quotation.pdf"
    pdf.output(str(path))
    return path
