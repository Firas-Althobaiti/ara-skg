"""Query subgraph: classify → nl2cypher → guard → run → synthesize."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from ara.nodes.query import (
    classify_query_node,
    guard_cypher_node,
    nl2cypher_node,
    run_cypher_node,
    synthesize_answer_node,
)
from ara.schemas import ARAState


def build_query_graph() -> Any:
    """Build and compile the query subgraph (linear flow with a guard)."""
    g = StateGraph(ARAState)

    g.add_node("classify_query", classify_query_node)
    g.add_node("nl2cypher", nl2cypher_node)
    g.add_node("guard_cypher", guard_cypher_node)
    g.add_node("run_cypher", run_cypher_node)
    g.add_node("synthesize_answer", synthesize_answer_node)

    g.add_edge(START, "classify_query")
    g.add_edge("classify_query", "nl2cypher")
    g.add_conditional_edges(
        "nl2cypher",
        lambda state: "guard_cypher" if state.get("cypher") else END,
        {"guard_cypher": "guard_cypher", END: END},
    )
    g.add_conditional_edges(
        "guard_cypher",
        lambda state: END if state.get("error") else "run_cypher",
        {END: END, "run_cypher": "run_cypher"},
    )
    g.add_edge("run_cypher", "synthesize_answer")
    g.add_edge("synthesize_answer", END)

    return g.compile()


__all__ = ["build_query_graph"]
