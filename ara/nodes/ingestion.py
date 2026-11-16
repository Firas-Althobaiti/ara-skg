from typing import Dict, Any
from ara.state import ARAState

async def ingest_papers(state: ARAState) -> Dict[str, Any]:
    """
    Placeholder node for the ingestion subgraph.
    Currently returns the unchanged state; in later phases it will:
    - route sources (pubmed/arxiv/pdf)
    - fetch papers,
    - chunk text,
    - persist to vector store.
    """
    # No‑op for now; downstream phases will fill in the logic.
    return state
