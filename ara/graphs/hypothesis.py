"""Hypothesis subgraph: generate → ground → rank → critique."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from ara.nodes.hypothesis import (
    critique_hypothesis_node,
    generate_hypotheses_node,
    ground_hypothesis_node,
    rank_hypotheses_node,
)
from ara.schemas import ARAState


def build_hypothesis_graph() -> Any:
    """Build and compile the hypothesis subgraph.

    Loops back to ``generate`` when the critique reports ``critique_error``.
    """
    g = StateGraph(ARAState)

    g.add_node("generate", generate_hypotheses_node)
    g.add_node("ground", ground_hypothesis_node)
    g.add_node("rank", rank_hypotheses_node)
    g.add_node("critique", critique_hypothesis_node)

    g.add_edge(START, "generate")
    g.add_edge("generate", "ground")
    g.add_edge("ground", "rank")
    g.add_edge("rank", "critique")
    g.add_conditional_edges(
        "critique",
        lambda state: "generate" if state.get("critique_error") else END,
        {"generate": "generate", END: END},
    )

    return g.compile()


__all__ = ["build_hypothesis_graph"]
