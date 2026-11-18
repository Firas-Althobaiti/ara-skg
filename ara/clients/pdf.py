"""PDF client – extract text from PDF files using PyMuPDF (fitz, imported lazily)."""

from ara.schemas.paper import Chunk, Paper


class PDFClient:
    def __init__(self) -> None:
        pass

    async def parse_pdf(self, source: str | bytes) -> Paper:
        import fitz  # PyMuPDF – imported lazily so the package imports without it

        path = source
        doc = fitz.open(path)
        full_text = ""
        chunks = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            full_text += text + "\n"
            # Very naive chunking: first 1000 characters per page
            chunk_text = text[:1000]
            if chunk_text:
                chunks.append(Chunk(text=chunk_text, paper_id="", span=page_num, embedding=None))

        paper = Paper(
            id="",
            source="pdf",
            title="",
            abstract=full_text[:500] if full_text else "",
            authors=[],
            year=0,
            url=None,
            full_text=full_text,
            chunks=chunks,
        )
        return paper

    async def close(self) -> None:
        pass
