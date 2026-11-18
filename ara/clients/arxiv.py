"""ArXiv client – async search of the arXiv API."""

import httpx

from ara.schemas.paper import Chunk, Paper


class ArXivClient:
    BASE_URL = "http://export.arxiv.org/api/query"

    def __init__(self) -> None:
        self.http = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        await self.http.aclose()

    async def search_arxiv(self, query: str, max_results: int = 10) -> list[Paper]:
        url = f"{self.BASE_URL}?search_query={query}&max_results={max_results}"
        resp = await self.http.get(url)
        resp.raise_for_status()
        data = resp.json()
        papers = []
        for entry in data.get("entry", []):
            title = entry.get("title", "")
            abstract = entry.get("abstract", "")
            authors = [a["name"] for a in entry.get("authors", [])]
            arxiv_id = entry.get("id", "")
            paper = Paper(
                id=arxiv_id,
                source="arxiv",
                title=title,
                abstract=abstract,
                authors=authors,
                year=0,
                url=None,
                full_text=None,
                chunks=[],
            )
            paper.chunks.append(
                Chunk(text="Placeholder abstract.", paper_id=arxiv_id, span=0, embedding=None)
            )
            papers.append(paper)
        return papers
