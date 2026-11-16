from typing import Dict, Any
from ara.state import ARAState
from ara.config import get_settings
from ara.clients.pubmed import PubMedClient
from ara.clients.arxiv import ArXivClient
from ara.clients.pdf import PDFClient
from ara.clients.vector import VectorStoreClient
import asyncio

async def route_sources(state: ARAState) -> Dict[str, Any]:
    """
    Decide which data source to use based on the task description.
    Returns a dict with a 'source' key.
    """
    task = state.task.lower()
    if "pubmed" in task:
        source = "pubmed"
    elif "arxiv" in task:
        source = "arxiv"
    elif "pdf" in task:
        source = "pdf"
    else:
        raise NotImplementedError(f"Unsupported source: {state.task}")

    return {"source": source}

async def fetch_papers(state: ARAState) -> Dict[str, Any]:
    src = state["source"]
    query = state.task  # simple: use the whole task as query

    if src == "pubmed":
        client = PubMedClient()
    elif src == "arxiv":
        client = ArXivClient()
    elif src == "pdf":
        client = PDFClient()
    else:
        raise ValueError(f"Unsupported source {src}")

    papers = await client.search_pubmed(query) if src == "pubmed" else \
             await client.search_arxiv(query) if src == "arxiv" else \
             await client.parse_pdf(query) if src == "pdf" else []

    return {"papers": papers}

async def chunk_papers(state: ARAState) -> Dict[str, Any]:
    papers = state.get("papers", [])
    vector_client = VectorStoreClient(persist_directory=get_settings().VECTOR_DIR)

    for paper in papers:
        # If paper has full_text, split into chunks; otherwise create a placeholder.
        if getattr(paper, "full_text", None):
            text = paper.full_text
            # naive chunking: 500 chars per chunk
            for i in range(0, len(text), 500):
                chunk_text = text[i:i+500]
                paper.chunks.append(
                    Chunk(
                        text=chunk_text,
                        paper_id=paper.id,
                        span=i,
                        embedding=None,
                    )
                )
        else:
            # placeholder chunk using abstract if available
            abstract = getattr(paper, "abstract", "")
            paper.chunks.append(
                Chunk(
                    text=abstract,
                    paper_id=paper.id,
                    span=0,
                    embedding=None,
                )
            )
    return {"papers": papers, "chunks": state.get("chunks", [])}

async def persist_chunks(state: ARAState) -> Dict[str, Any]:
    # Ensure vector client is ready
    vector_client = VectorStoreClient(persist_directory=get_settings().VECTOR_DIR)

    # Flatten all chunks from all papers
    all_chunks = []
    for paper in state.get("papers", []):
        all_chunks.extend(paper.chunks)

    await vector_client.add_chunks(
        all_chunks,
        [c["metadata"] for c in all_chunks],
        [f"{c['paper_id']}_{i}" for i, c in enumerate(all_chunks)],
    )
    return {"papers": state.get("papers", []), "chunks": state.get("chunks", [])}

async def error(state: ARAState) -> Dict[str, Any]:
    """Node executed when no papers are found."""
    state["errors"].append("No papers found for the given task.")
    return state
