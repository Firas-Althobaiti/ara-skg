"""Ingestion nodes: fetch papers from a source, chunk them, persist chunks.

Papers and chunks may arrive either as Pydantic models (:class:`Paper` /
:class:`Chunk`) or as plain dicts — the ``_get`` helper normalises access.

The special source ``"mock"`` returns the built-in demo corpus
(:func:`mock_papers`), which lets the CLI and the end-to-end demo run fully
offline with a mocked LLM.
"""

from __future__ import annotations

from typing import Any, cast

from ara.clients import vector as vector_module
from ara.config import get_settings
from ara.schemas import ARAState, Chunk, Paper


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Attribute-or-key access for models and dicts alike."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def mock_papers() -> list[Paper]:
    """Three small biomedical demo papers used by ``--mock`` / the demo.

    Abstracts use the mock-extractor format ``"Subject - predicate - Object; ..."``
    so the deterministic (mocked-LLM) relation extractor can parse them
    without any network or API key.
    """
    specs = [
        (
            "PMID:1001",
            "BRCA1 germline mutations and DNA repair in breast cancer",
            "BRCA1 - associated_with - Breast cancer; "
            "BRCA1 - regulates - RAD51; "
            "RAD51 - involved_in - DNA repair",
        ),
        (
            "PMID:1002",
            "PARP inhibition with olaparib in BRCA-mutated cancers",
            "Olaparib - inhibits - PARP1; "
            "PARP1 - involved_in - DNA repair; "
            "Olaparib - treats - Breast cancer",
        ),
        (
            "PMID:1003",
            "TP53 regulation of BRCA1 and tamoxifen response in breast cancer",
            "TP53 - regulates - BRCA1; "
            "TP53 - associated_with - Breast cancer; "
            "Tamoxifen - treats - Breast cancer",
        ),
    ]
    papers: list[Paper] = []
    for pid, title, abstract in specs:
        papers.append(
            Paper(
                id=pid,
                source="mock",
                title=title,
                abstract=abstract,
                authors=["ARA Demo"],
                year=2024,
                url=None,
                full_text=None,
                chunks=[],
            )
        )
    return papers


async def route_sources(state: ARAState) -> dict[str, Any]:
    """Decide which source to fetch from based on ``state['task']``."""
    task = state["task"].lower()
    if "mock" in task or "demo" in task:
        source = "mock"
    elif "pubmed" in task:
        source = "pubmed"
    elif "arxiv" in task:
        source = "arxiv"
    elif "pdf" in task:
        source = "pdf"
    else:
        raise NotImplementedError(f"Unsupported source: {state['task']}")
    return {"source": source}


async def fetch_papers(state: ARAState) -> dict[str, Any]:
    """Fetch papers from the routed source (``mock`` needs no network)."""
    src = state["source"]
    query = state["task"]
    if src == "mock":
        papers = mock_papers()
    elif src == "pubmed":
        from ara.clients.pubmed import PubMedClient

        client: Any = PubMedClient(api_key=get_settings().NCBI_API_KEY)
        papers = await client.search_pubmed(query)
        await client.close()
    elif src == "arxiv":
        from ara.clients.arxiv import ArXivClient

        client = ArXivClient()
        papers = await client.search_arxiv(query)
        await client.close()
    elif src == "pdf":
        from ara.clients.pdf import PDFClient

        client = PDFClient()
        paper = await client.parse_pdf(query)
        papers = [paper]
        await client.close()
    else:
        raise ValueError(f"Unsupported source {src}")
    return {"papers": papers}


async def chunk_papers(state: ARAState) -> dict[str, Any]:
    """Split each paper's full text (or abstract) into ~500-char chunks."""
    papers = state.get("papers", [])
    all_chunks: list[Chunk] = []
    for paper in papers:
        full_text = _get(paper, "full_text", None)
        paper_chunks = _get(paper, "chunks", [])
        if full_text:
            for i in range(0, len(full_text), 500):
                chunk = Chunk(
                    text=full_text[i : i + 500],
                    paper_id=_get(paper, "id", ""),
                    span=i,
                    embedding=None,
                )
                paper_chunks.append(chunk)
                all_chunks.append(chunk)
        else:
            abstract = _get(paper, "abstract", "") or ""
            chunk = Chunk(
                text=abstract,
                paper_id=_get(paper, "id", ""),
                span=0,
                embedding=None,
            )
            paper_chunks.append(chunk)
            all_chunks.append(chunk)
    state["papers"] = papers
    state["chunks"] = state.get("chunks", []) + [c.model_dump() for c in all_chunks]
    return {"papers": papers, "chunks": state["chunks"]}


async def persist_chunks(state: ARAState) -> dict[str, Any]:
    """Write all paper chunks to the vector store (Chroma, lazily created)."""
    vector_client = vector_module.VectorStoreClient(persist_directory=get_settings().VECTOR_DIR)
    chunk_dicts: list[dict[str, Any]] = []
    metadatas: list[dict[str, Any]] = []
    ids: list[str] = []
    for paper in state.get("papers", []):
        for i, chunk in enumerate(_get(paper, "chunks", [])):
            text = _get(chunk, "text", "")
            paper_id = _get(chunk, "paper_id", _get(paper, "id", ""))
            span = _get(chunk, "span", 0)
            chunk_dicts.append({"text": text, "metadata": {"paper_id": paper_id, "span": span}})
            metadatas.append({"paper_id": paper_id, "span": span})
            ids.append(f"{paper_id}_{i}")
    if chunk_dicts:
        await vector_client.add_chunks(chunk_dicts, metadatas, ids)
    state["chunks"] = state.get("chunks", [])
    return {"papers": state.get("papers", []), "chunks": state["chunks"]}


async def error(state: ARAState) -> dict[str, Any]:
    """Terminal node for the no-papers path."""
    return {"errors": ["No papers found for the given task."]}


async def ingest_papers(state: ARAState) -> dict[str, Any]:
    """Compose route → fetch → chunk into a single node.

    Vector persistence is handled by :func:`persist_chunks` in the ingestion
    graph (only when ``state['persist']`` is truthy), keeping this helper
    offline-safe.
    """
    merged: dict[str, Any] = dict(state)
    for node in (route_sources, fetch_papers, chunk_papers):
        merged.update(await node(cast(ARAState, merged)))
        merged = {**state, **merged}
    update: dict[str, Any] = {k: merged[k] for k in ("source", "papers", "chunks") if k in merged}
    state.update(cast(ARAState, update))
    return update


__all__ = [
    "route_sources",
    "fetch_papers",
    "chunk_papers",
    "persist_chunks",
    "ingest_papers",
    "error",
    "mock_papers",
]
