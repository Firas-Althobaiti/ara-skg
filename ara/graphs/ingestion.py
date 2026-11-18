"""Ingestion subgraph: route → fetch → (error | chunk → [persist] )."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from ara.nodes.ingestion import chunk_papers, error, fetch_papers, persist_chunks, route_sources
from ara.schemas import ARAState


def build_ingestion_graph() -> Any:
    """Build and compile the ingestion subgraph.

    Flow::

        START → route_sources → fetch_papers
                                    ├── (no papers) → error → END
                                    └── (papers)    → chunk_papers
                                                       → persist_chunks (only if
                                                          state['persist']) → END
    """
    g = StateGraph(ARAState)

    g.add_node("route_sources", route_sources)
    g.add_node("fetch_papers", fetch_papers)
    g.add_node("chunk_papers", chunk_papers)
    g.add_node("persist_chunks", persist_chunks)
    g.add_node("error", error)

    g.add_edge(START, "route_sources")
    g.add_edge("route_sources", "fetch_papers")
    g.add_conditional_edges(
        "fetch_papers",
        lambda state: "error" if not state.get("papers") else "chunk_papers",
        {"error": "error", "chunk_papers": "chunk_papers"},
    )
    g.add_conditional_edges(
        "chunk_papers",
        lambda state: "persist_chunks" if state.get("persist") else END,
        {"persist_chunks": "persist_chunks", END: END},
    )
    g.add_edge("persist_chunks", END)
    g.add_edge("error", END)

    return g.compile()


__all__ = ["build_ingestion_graph"]
