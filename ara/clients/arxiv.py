"""arXiv client: params-encoded Atom API with real abstracts.

Query parameters are passed via httpx ``params`` (URL-encoded), so spaces
and ``&`` in the query can never break the URL. The Atom feed is parsed
with the stdlib :mod:`xml.etree.ElementTree`; each entry's ``<summary>``
IS the abstract (no more ``"Placeholder abstract."``).
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import httpx

from ara.clients._retry import RETRY
from ara.schemas import Paper

API_URL = "https://export.arxiv.org/api/query"  # http:// 301-redirects to https; httpx does not follow by default
ATOM = "{http://www.w3.org/2005/Atom}"


class ArXivParseError(Exception):
    """arXiv API returned a feed that could not be parsed."""


class ArXivClient:
    def __init__(self, timeout: float = 30.0) -> None:
        self.http = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self.http.aclose()

    @RETRY
    async def _get_feed(self, query: str, limit: int) -> ET.Element:
        resp = await self.http.get(
            API_URL,
            params={"search_query": f"all:{query}", "start": 0, "max_results": limit},
        )
        resp.raise_for_status()  # non-2xx -> HTTPStatusError -> retried by @RETRY
        try:
            return ET.fromstring(resp.text)
        except ET.ParseError as exc:
            raise ArXivParseError("arXiv API returned a malformed Atom feed") from exc

    async def search_arxiv(self, query: str, max_results: int = 10) -> list[Paper]:
        root = await self._get_feed(query, max_results)
        papers: list[Paper] = []
        for entry in root.findall(f"{ATOM}entry"):
            raw_id = (entry.findtext(f"{ATOM}id") or "").strip()
            paper_id = re.sub(r"v\d+$", "", raw_id)  # strip version suffix (…/2301.00001v2)
            title = " ".join((entry.findtext(f"{ATOM}title") or "").split())
            summary = " ".join((entry.findtext(f"{ATOM}summary") or "").split())
            authors = [
                " ".join((a.findtext(f"{ATOM}name") or "").split())
                for a in entry.findall(f"{ATOM}author")
                if (a.findtext(f"{ATOM}name") or "").strip()
            ]
            published = (entry.findtext(f"{ATOM}published") or "")[:4]
            year = int(published) if published.isdigit() else 0
            papers.append(
                Paper(
                    id=paper_id or raw_id,
                    source="arxiv",
                    title=title,
                    abstract=summary,  # the <summary> IS the abstract
                    authors=authors,
                    year=year,
                    url=raw_id or None,
                    full_text=None,
                    chunks=[],  # chunking happens downstream in chunk_papers
                )
            )
        return papers
