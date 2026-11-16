import asyncio
from ara.state import ARAState
from ara.graphs.ingestion import build_ingestion_graph
from ara.nodes.ingestion import route_sources, fetch_papers, chunk_papers, persist_chunks, error

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
async def test_fetch_papers_mock(monkeypatch):
    async def mock_fetch(state):
        paper = Paper(
            id="PMID:001",
            source="pubmed",
            title="Test Paper",
            abstract="Abstract text.",
            authors=["Alice"],
            year=2024,
            url=None,
            full_text="x" * 1500,
            chunks=[],
        )
        return {"papers": [paper]}

    monkeypatch.setattr("ara.nodes.ingestion.fetch_papers", mock_fetch)

    state = ARAState(task="ingest pubmed", papers=[])
    papers = await fetch_papers(state)
    assert len(papers) == 1
    assert papers[0].id == "PMID:001"

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
    chunks = await chunk_papers(state)
    assert len(paper.chunks) == 2  # split into two ~300 char chunks

@pytest.mark.asyncio
async def test_persist_chunks(monkeypatch):
    # mock vector client
    class DummyVectorClient:
        async def add_chunks(self, chunks, metadatas, ids):
            pass

    monkeypatch.setattr("ara.clients.vector.VectorStoreClient", lambda persist_directory: DummyVectorClient())

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
