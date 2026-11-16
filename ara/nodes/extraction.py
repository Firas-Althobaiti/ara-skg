from typing import Dict, Any
from ara.state import ARAState

async def extract_entities(state: ARAState) -> Dict[str, Any]:
    """
    Placeholder node for entity extraction.
    Returns the state unchanged; later will call the LLM‑based extractor,
    perform entity linking, and produce a list of Entity objects.
    """
    return state

async def extract_relations(state: ARAState) -> Dict[str, Any]:
    """
    Placeholder node for relation extraction.
    Will generate Triple objects from text, apply confidence scoring,
    and attach provenance.
    """
    return state

async def link_entities(state: ARAState) -> Dict[str, Any]:
    """
    Placeholder node for entity linking / deduplication.
    """
    return state

async def validate_triples(state: ARAState) -> Dict[str, Any]:
    """
    Placeholder node for critic validation.
    Rejects triples with low confidence or missing provenance.
    """
    return state
