"""PDF client – extract text from PDF files using PyMuPDF (fitz, imported lazily)."""

from __future__ import annotations

import os

from ara.logging import get_logger
from ara.schemas.paper import Chunk, Paper

MAX_PDF_BYTES = 50 * 1024 * 1024  # 50 MB cap on input PDFs


class PDFParseError(Exception):
    """A PDF could not be read or parsed (malformed / encrypted / missing)."""

    def __init__(self, message: str, path: str) -> None:
        super().__init__(f"{message} (path={path})")
        self.path = path


class PDFClient:
    def __init__(self) -> None:
        pass

    async def parse_pdf(self, path: str, *, paper_id: str) -> Paper:
        """Parse ``path`` into a Paper whose chunks all carry ``paper_id``.

        ``paper_id`` is keyword-only and required — an empty one would break
        triple provenance and the grounding eval. Raises ``ValueError`` for
        empty id / oversized files, ``PDFParseError`` for unreadable PDFs.
        """
        if not paper_id:
            raise ValueError("paper_id is required")
        try:
            size = os.path.getsize(path)
        except OSError as exc:
            raise PDFParseError("cannot read PDF file", path) from exc
        if size > MAX_PDF_BYTES:
            raise ValueError(f"PDF too large: {size} bytes exceeds {MAX_PDF_BYTES} (path={path})")

        import fitz  # PyMuPDF – imported lazily so the package imports without it

        logger = get_logger("ara.pdf")
        try:
            doc = fitz.open(path)
            full_text = ""
            chunks: list[Chunk] = []
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                full_text += text + "\n"
                # Very naive chunking: first 1000 characters per page
                chunk_text = text[:1000]
                if chunk_text:
                    chunks.append(
                        Chunk(text=chunk_text, paper_id=paper_id, span=page_num, embedding=None)
                    )
            doc.close()
        except Exception as exc:
            logger.error("pdf parse failed", path=path, error=str(exc))
            raise PDFParseError(f"failed to parse PDF: {exc}", path) from exc

        return Paper(
            id=paper_id,
            source="pdf",
            title=os.path.splitext(os.path.basename(path))[0],
            abstract=full_text[:500] if full_text else "",
            authors=[],
            year=0,
            url=None,
            full_text=full_text,
            chunks=chunks,
        )

    async def close(self) -> None:
        pass
