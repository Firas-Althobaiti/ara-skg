import pytest

from ara.nodes.ingestion import chunk_papers, fetch_papers, persist_chunks, route_sources
from ara.schemas import ARAState, Paper


@pytest.mark.asyncio
async def test_route_sources():
    state = ARAState(task="ingest pubmed")
    result = await route_sources(state)
    assert result["source"] == "pubmed"


@pytest.mark.asyncio
async def test_route_sources_arxiv():
    state = ARAState(task="ingest arxiv")
    result = await route_sources(state)
    assert result["source"] == "arxiv"


@pytest.mark.asyncio
async def test_route_sources_pdf():
    state = ARAState(task="ingest pdf")
    result = await route_sources(state)
    assert result["source"] == "pdf"


@pytest.mark.asyncio
async def test_route_sources_unknown():
    state = ARAState(task="unknown")
    with pytest.raises(NotImplementedError):
        await route_sources(state)


@pytest.mark.asyncio
async def test_fetch_papers_mock():
    state = ARAState(task="ingest mock corpus", papers=[])
    state.update(await route_sources(state))
    result = await fetch_papers(state)
    papers = result["papers"]
    assert len(papers) == 3  # mock corpus has 3 demo papers
    assert papers[0].id == "PMID:1001"


@pytest.mark.asyncio
async def test_chunk_papers():
    paper = Paper(
        id="PMID:001",
        source="pubmed",
        title="Test",
        abstract="Abstract.",
        authors=["A"],
        year=2024,
        url=None,
        full_text="a" * 600,  # enough for two chunks
        chunks=[],
    )
    state = ARAState(papers=[paper])
    await chunk_papers(state)
    assert len(paper.chunks) == 2  # split into two ~300 char chunks


@pytest.mark.asyncio
async def test_persist_chunks(monkeypatch):
    # mock vector client
    class DummyVectorClient:
        async def add_chunks(self, chunks, metadatas, ids):
            pass

    monkeypatch.setattr(
        "ara.clients.vector.VectorStoreClient", lambda persist_directory: DummyVectorClient()
    )

    state = ARAState(
        papers=[
            Paper(
                id="PMID:001",
                source="pubmed",
                title="Test",
                abstract="Abstract.",
                authors=["A"],
                year=2024,
                url=None,
                full_text="x" * 500,
                chunks=[],
            )
        ]
    )
    await persist_chunks(state)
    # No exception means success


@pytest.mark.asyncio
async def test_fetch_papers_strips_ingest_prefix(monkeypatch):
    """task 'ingest pubmed BRCA1 breast cancer' must search 'BRCA1 breast cancer'."""
    import ara.clients.pubmed as pubmed_mod

    captured: dict = {}

    class FakeClient:
        def __init__(self, api_key=None):
            captured["api_key"] = api_key

        async def search_pubmed(self, query, retmax=20):
            captured["query"] = query
            return []

        async def close(self):
            pass

    monkeypatch.setattr(pubmed_mod, "PubMedClient", FakeClient)
    state = ARAState(task="ingest pubmed BRCA1 breast cancer")
    state.update(await route_sources(state))
    await fetch_papers(state)
    assert captured["query"] == "BRCA1 breast cancer"
