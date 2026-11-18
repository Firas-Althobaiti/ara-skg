"""Extraction subgraph: entities → relations → link → validate."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from ara.nodes.extraction import (
    extract_entities_node,
    extract_relations_node,
    link_entities_node,
    validate_triples_node,
)
from ara.schemas import ARAState


def build_extraction_graph() -> Any:
    """Build and compile the extraction subgraph (linear flow)."""
    g = StateGraph(ARAState)

    g.add_node("extract_entities", extract_entities_node)
    g.add_node("extract_relations", extract_relations_node)
    g.add_node("link_entities", link_entities_node)
    g.add_node("validate_triples", validate_triples_node)

    g.add_edge(START, "extract_entities")
    g.add_edge("extract_entities", "extract_relations")
    g.add_edge("extract_relations", "link_entities")
    g.add_edge("link_entities", "validate_triples")
    g.add_edge("validate_triples", END)

    return g.compile()


__all__ = ["build_extraction_graph"]
