from typing import Dict, Any
from ara.state import ARAState

async def classify_query(state: ARAState) -> Dict[str, Any]:
    """
    Determine the intent of the user query (e.g., fetch, query, hypothesize).
    """
    return state

async def nl2cypher(state: ARAState) -> Dict[str, Any]:
    """
    Convert a natural‑language question into a Cypher pattern and parameters.
    Returns the Cypher string and param dict.
    """
    return state

async def guard_cypher(state: ARAState) -> Dict[str, Any]:
    """
    Reject queries containing write‑operations (CREATE, DELETE, MERGE).
    If rejected, the caller may retry with a different natural‑language phrasing.
    """
    return state

async def run_cypher(state: ARAState) -> Dict[str, Any]:
    """
    Execute the Cypher query against the KG backend and return the raw result set.
    """
    return state

async def synthesize_answer(state: ARAState) -> Dict[str, Any]:
    """
    Combine subgraph context with vector search results to produce a concise answer.
    """
    return state
