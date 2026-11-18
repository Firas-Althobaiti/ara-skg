"""Main graph – wires all subgraphs together with a supervisor and checkpointer."""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from ara.graphs.evolution import build_evolution_graph
from ara.graphs.experiment import build_experiment_graph
from ara.graphs.extraction import build_extraction_graph
from ara.graphs.graph_update import build_graph_update_graph
from ara.graphs.hypothesis import build_hypothesis_graph
from ara.graphs.ingestion import build_ingestion_graph
from ara.graphs.query import build_query_graph
from ara.nodes.supervisor import classify_intent_node, critic_node, replan_node
from ara.schemas import ARAState

SUBGRAPHS = {
    "ingestion": build_ingestion_graph,
    "extraction": build_extraction_graph,
    "graph_update": build_graph_update_graph,
    "query": build_query_graph,
    "hypothesis": build_hypothesis_graph,
    "experiment": build_experiment_graph,
    "evolution": build_evolution_graph,
}


def build_main_graph(checkpointer: BaseCheckpointSaver | None = None) -> Any:
    """Build the top-level StateGraph.

    Nodes:
        - supervisor (classify_intent_node)
        - one node per compiled subgraph
        - critic (critic_node)
        - replan (replan_node)

    Edges:
        START → supervisor
        supervisor → subgraph (conditional on ``state['route']``)
        subgraph → critic
        critic → END (or replan → supervisor if errors)

    ``graph_update`` is interrupted before execution so a human can approve
    KG writes (resume by re-invoking with the same thread).
    """
    g = StateGraph(ARAState)

    g.add_node("supervisor", classify_intent_node)
    g.add_node("critic", critic_node)
    g.add_node("replan", replan_node)

    for name, builder in SUBGRAPHS.items():
        g.add_node(name, builder())

    g.add_edge(START, "supervisor")

    g.add_conditional_edges(
        "supervisor",
        lambda s: s.get("route", "end"),
        {name: name for name in SUBGRAPHS} | {"end": END},
    )

    for name in SUBGRAPHS:
        g.add_edge(name, "critic")

    g.add_conditional_edges(
        "critic",
        lambda s: "replan" if s.get("needs_replan") else END,
        {"replan": "replan", END: END},
    )
    g.add_edge("replan", "supervisor")

    return g.compile(
        checkpointer=checkpointer,
        interrupt_before=["graph_update"],  # human approval before KG writes
    )


def _default_checkpointer() -> BaseCheckpointSaver:
    """SQLite checkpointer when available, otherwise in-memory.

    Note: the sync ``SqliteSaver`` is used here because this factory runs at
    import time (module-level ``app``) where no event loop exists; async code
    paths should pass an ``AsyncSqliteSaver`` explicitly (see the e2e tests).
    """
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver

        return SqliteSaver("checkpoints.sqlite")
    except ImportError:
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver()


# Singleton app with a checkpointer (SQLite if the extra is installed).
app = build_main_graph(_default_checkpointer())

__all__ = ["build_main_graph", "app", "SUBGRAPHS"]
