"""Graph-update subgraph: resolve → ensure schema → upsert → (rollback | END)."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from ara.nodes.graph_update import (
    ensure_schema_node,
    resolve_triples_node,
    rollback_on_error,
    upsert_kg_node,
)
from ara.schemas import ARAState


def build_graph_update_graph() -> Any:
    """Build and compile the graph-update subgraph."""
    g = StateGraph(ARAState)

    g.add_node("resolve_triples", resolve_triples_node)
    g.add_node("ensure_schema", ensure_schema_node)
    g.add_node("upsert_kg", upsert_kg_node)
    g.add_node("rollback_on_error", rollback_on_error)

    g.add_edge(START, "resolve_triples")
    g.add_edge("resolve_triples", "ensure_schema")
    g.add_edge("ensure_schema", "upsert_kg")
    g.add_conditional_edges(
        "upsert_kg",
        lambda state: "rollback_on_error" if state.get("errors") else END,
        {"rollback_on_error": "rollback_on_error", END: END},
    )
    g.add_edge("rollback_on_error", END)

    return g.compile()


__all__ = ["build_graph_update_graph"]
