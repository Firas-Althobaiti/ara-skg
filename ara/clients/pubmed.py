"""PubMed client – async search and basic paper extraction."""

import httpx

from ara.schemas.paper import Chunk, Paper


class PubMedClient:
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self):
        self.http = httpx.AsyncClient(timeout=30.0)

    async def _request(self, endpoint: str, params: dict) -> dict:
        resp = await self.http.get(f"{self.BASE_URL}/{endpoint}", params=params)
        resp.raise_for_status()
        return resp.json()

    async def search_pubmed(self, query: str, retmax: int = 20) -> list[Paper]:
        # ESearch
        params = {"db": "pubmed", "term": query, "retmode": "json", "retmax": retmax}
        esearch = await self._request("esearch", params)
        id_list = esearch["esearchresult"]["idlist"]

        papers = []
        for uid in id_list:
            params = {"db": "pubmed", "id": uid, "retmode": "json"}
            esummary = await self._request("esummary", params)
            title = esummary["result"].get("article-title", [""])[0]
            abstract = esummary["result"].get("abstract", {}).get("abstract-text", [""])[0]
            paper = Paper(
                id=uid,
                source="pubmed",
                title=title,
                abstract=abstract,
                authors=[],
                year=0,
                url=None,
                full_text=None,
                chunks=[],
            )
            # placeholder chunk
            paper.chunks.append(
                Chunk(text="Placeholder abstract.", paper_id=uid, span=0, embedding=None)
            )
            papers.append(paper)
        return papers

    async def close(self):
        await self.http.aclose()
