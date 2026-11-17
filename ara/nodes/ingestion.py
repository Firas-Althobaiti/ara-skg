from typing import Any

from ara.clients.arxiv import ArXivClient
from ara.clients.pdf import PDFClient
from ara.clients.pubmed import PubMedClient
from ara.clients.vector import VectorStoreClient
from ara.config import get_settings
from ara.schemas import Chunk
from ara.state import ARAState


async def route_sources(state: ARAState) -> dict[str, Any]:
    task = state["task"].lower()
    if "pubmed" in task:
        source = "pubmed"
    elif "arxiv" in task:
        source = "arxiv"
    elif "pdf" in task:
        source = "pdf"
    else:
        raise NotImplementedError(f"Unsupported source: {state['task']}")
    return {"source": source}


async def fetch_papers(state: ARAState) -> dict[str, Any]:
    src = state["source"]
    query = state["task"]
    if src == "pubmed":
        client = PubMedClient()
        papers = await client.search_pubmed(query)
    elif src == "arxiv":
        client = ArXivClient()
        papers = await client.search_arxiv(query)
    elif src == "pdf":
        client = PDFClient()
        papers = await client.parse_pdf(query)
    else:
        raise ValueError(f"Unsupported source {src}")
    return {"papers": papers}


async def chunk_papers(state: ARAState) -> dict[str, Any]:
    papers = state.get("papers", [])
    for paper in papers:
        if getattr(paper, "full_text", None):
            text = paper.full_text
            for i in range(0, len(text), 500):
                chunk_text = text[i : i + 500]
                paper.chunks.append(
                    Chunk(text=chunk_text, paper_id=paper.id, span=i, embedding=None)
                )
        else:
            abstract = getattr(paper, "abstract", "")
            paper.chunks.append(
                Chunk(text=abstract, paper_id=paper.id, span=0, embedding=None)
            )
    return {"papers": papers, "chunks": state.get("chunks", [])}


async def persist_chunks(state: ARAState) -> dict[str, Any]:
    vector_client = VectorStoreClient(persist_directory=get_settings().VECTOR_DIR)
    all_chunks = []
    for paper in state.get("papers", []):
        all_chunks.extend(paper.chunks)
    if all_chunks:
        await vector_client.add_chunks(
            texts=[c.text for c in all_chunks],
            metadatas=[{"paper_id": c.paper_id, "span": c.span} for c in all_chunks],
            ids=[f"{c.paper_id}_{i}" for i, c in enumerate(all_chunks)],
        )
    return {"papers": state.get("papers", []), "chunks": state.get("chunks", [])}


async def error(state: ARAState) -> dict[str, Any]:
    return {"errors": ["No papers found for the given task."]}
