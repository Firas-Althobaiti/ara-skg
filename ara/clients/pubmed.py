"""PubMed client: batched efetch with real abstract parsing.

``esearch`` (one request) returns the PMID list; a single ``efetch``
request with ``rettype=abstract&retmode=xml`` returns the whole batch as
PubMed XML, parsed with the stdlib :mod:`xml.etree.ElementTree` (no lxml,
no new dependencies). This replaces the old N+1 esummary loop that read
non-existent keys and stored ``"Placeholder abstract."``.

Rate limits: unauthenticated NCBI clients are limited to ~3 req/s (429s);
passing ``api_key`` (``NCBI_API_KEY``) raises the limit to 10 req/s.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import httpx

from ara.clients._retry import RETRY
from ara.schemas import Paper

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class PubMedParseError(Exception):
    """efetch returned XML that could not be parsed."""


class PubMedClient:
    def __init__(self, api_key: str | None = None, timeout: float = 30.0) -> None:
        self.api_key = api_key
        self.http = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self.http.aclose()

    @RETRY
    async def _request(self, endpoint: str, params: dict[str, Any]) -> httpx.Response:
        """Single GET with retry; ``api_key`` goes via params, never string concat."""
        if self.api_key:
            params = {**params, "api_key": self.api_key}
        resp = await self.http.get(f"{BASE_URL}/{endpoint}", params=params)
        resp.raise_for_status()  # 429/5xx -> HTTPStatusError -> retried by @RETRY
        return resp

    async def _esearch(self, query: str, retmax: int) -> list[str]:
        resp = await self._request(
            "esearch",
            {"db": "pubmed", "term": query, "retmode": "json", "retmax": retmax},
        )
        idlist = resp.json().get("esearchresult", {}).get("idlist", [])
        return [str(i) for i in idlist]

    async def _efetch(self, pmids: list[str]) -> ET.Element:
        """One batch request for all PMIDs; XML parsed with stdlib ElementTree."""
        resp = await self._request(
            "efetch",
            {"db": "pubmed", "id": ",".join(pmids), "rettype": "abstract", "retmode": "xml"},
        )
        try:
            return ET.fromstring(resp.text)
        except ET.ParseError as exc:
            raise PubMedParseError(
                f"efetch returned malformed XML for {len(pmids)} PMID(s)"
            ) from exc

    @staticmethod
    def _parse_article(article: ET.Element) -> Paper | None:
        citation = article.find("MedlineCitation")
        if citation is None:
            return None
        pmid = (citation.findtext("PMID") or "").strip()
        art = citation.find("Article")
        if art is None or not pmid:
            return None

        title = (art.findtext("ArticleTitle") or "").strip()

        # Structured abstracts have several <AbstractText> sections — join them.
        abstract_parts: list[str] = []
        abstract_el = art.find("Abstract")
        if abstract_el is not None:
            for at in abstract_el.findall("AbstractText"):
                if at.text:
                    abstract_parts.append(at.text.strip())
        abstract = " ".join(abstract_parts)

        authors: list[str] = []
        author_list = art.find("AuthorList")
        if author_list is not None:
            for a in author_list.findall("Author"):
                last = (a.findtext("LastName") or "").strip()
                fore = (a.findtext("ForeName") or "").strip() or (
                    a.findtext("Initials") or ""
                ).strip()
                if last:
                    authors.append(f"{last} {fore}".strip())

        year = 0
        pub_date = art.find("Journal/JournalIssue/PubDate")
        if pub_date is not None:
            year_text = pub_date.findtext("Year") or pub_date.findtext("MedlineDate") or ""
            digits = "".join(ch for ch in year_text if ch.isdigit())
            if digits:
                year = int(digits[:4])

        # DOI (ArticleIdList, IdType="doi") — Paper has no doi field yet; the
        # value is located here so it is ready when a field is added.
        pubmed_data = article.find("PubmedData/ArticleIdList")
        if pubmed_data is not None:
            for aid in pubmed_data.findall("ArticleId"):
                if aid.get("IdType") == "doi" and aid.text:
                    break

        return Paper(
            id=f"PMID:{pmid}",
            source="pubmed",
            title=title,
            abstract=abstract,  # real abstract, never "Placeholder abstract."
            authors=authors,
            year=year,
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            full_text=None,
            chunks=[],  # chunking happens downstream in chunk_papers
        )

    async def search_pubmed(self, query: str, retmax: int = 20) -> list[Paper]:
        """esearch -> one batched efetch -> parse. Raises ValueError on 0 hits."""
        pmids = await self._esearch(query, retmax)
        if not pmids:
            raise ValueError(f"No PubMed results for query: {query!r}")
        root = await self._efetch(pmids)
        papers: list[Paper] = []
        for article in root.findall("PubmedArticle"):
            paper = self._parse_article(article)
            if paper is not None:
                papers.append(paper)
        return papers
