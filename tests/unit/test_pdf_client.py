"""Unit tests for the PDF client (issue #17): required paper_id, size cap,
domain error on corrupt files, and provenance on every chunk."""

from __future__ import annotations

from pathlib import Path

import pytest

from ara.clients import pdf as pdf_module
from ara.clients.pdf import MAX_PDF_BYTES, PDFClient, PDFParseError


def _make_pdf(path: Path, text: str = "BRCA1 - inhibits - PARP1") -> None:
    import fitz  # PyMuPDF (dev extra)

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


@pytest.mark.asyncio
async def test_missing_paper_id_raises_value_error(tmp_path: Path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    _make_pdf(pdf_path)
    client = PDFClient()
    with pytest.raises(ValueError, match="paper_id is required"):
        await client.parse_pdf(str(pdf_path), paper_id="")


@pytest.mark.asyncio
async def test_oversized_file_raises_value_error_with_size(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pdf_path = tmp_path / "big.pdf"
    _make_pdf(pdf_path)
    real_size = pdf_path.stat().st_size
    monkeypatch.setattr(pdf_module, "MAX_PDF_BYTES", 10)  # shrink the cap for the test
    client = PDFClient()
    with pytest.raises(ValueError, match=str(real_size)):
        await client.parse_pdf(str(pdf_path), paper_id="PMID_1")
    assert MAX_PDF_BYTES == 50 * 1024 * 1024  # module default unchanged


@pytest.mark.asyncio
async def test_corrupt_pdf_raises_domain_error(tmp_path: Path) -> None:
    bad = tmp_path / "broken.pdf"
    bad.write_bytes(b"this is not a real pdf")
    client = PDFClient()
    with pytest.raises(PDFParseError, match="broken.pdf"):
        await client.parse_pdf(str(bad), paper_id="PMID_1")


@pytest.mark.asyncio
async def test_valid_pdf_chunks_carry_paper_id(tmp_path: Path) -> None:
    pdf_path = tmp_path / "my_paper.pdf"
    _make_pdf(pdf_path, "TP53 - regulates - BRCA1; BRCA1 - associated_with - Breast cancer")
    client = PDFClient()
    paper = await client.parse_pdf(str(pdf_path), paper_id="PMID_123")
    assert paper.id == "PMID_123"
    assert paper.chunks, "expected at least one chunk"
    assert all(c.paper_id == "PMID_123" for c in paper.chunks)  # provenance survives
    assert "TP53" in paper.full_text
