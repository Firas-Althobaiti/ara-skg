"""Evolution subgraph: window → detect → summarize."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from ara.nodes.evolution import (
    detect_changes_node,
    summarize_evolution_node,
    window_triples_node,
)
from ara.schemas import ARAState


def build_evolution_graph() -> Any:
    """Build and compile the evolution subgraph."""
    g = StateGraph(ARAState)

    g.add_node("window", window_triples_node)
    g.add_node("detect", detect_changes_node)
    g.add_node("summarize", summarize_evolution_node)

    g.add_edge(START, "window")
    g.add_edge("window", "detect")
    g.add_conditional_edges(
        "detect",
        lambda state: "window" if state.get("evolution_error") else "summarize",
        {"window": "window", "summarize": "summarize"},
    )
    g.add_edge("summarize", END)

    return g.compile()


__all__ = ["build_evolution_graph"]
