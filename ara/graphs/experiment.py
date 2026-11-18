"""Experiment subgraph: propose → validate (loops on validation error)."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from ara.nodes.experiment import propose_experiment_node, validate_feasibility_node
from ara.schemas import ARAState


def build_experiment_graph() -> Any:
    """Build and compile the experiment subgraph."""
    g = StateGraph(ARAState)

    g.add_node("propose", propose_experiment_node)
    g.add_node("validate", validate_feasibility_node)

    g.add_edge(START, "propose")
    g.add_edge("propose", "validate")
    g.add_conditional_edges(
        "validate",
        lambda state: "propose" if state.get("experiment_error") else END,
        {"propose": "propose", END: END},
    )

    return g.compile()


__all__ = ["build_experiment_graph"]
