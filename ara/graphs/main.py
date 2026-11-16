# File: ara/graphs/main.py
"""Main graph – wires all subgraphs together with a supervisor and checkpointer."""

from langgraph import StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver
from ara.state import ARAState
from ara.graphs.ingestion import build_ingestion_graph
from ara.graphs.extraction import build_extraction_graph
from ara.graphs.graph_update import build_graph_update_graph
from ara.graphs.query import build_query_graph
from ara.graphs.hypothesis import build_hypothesis_graph
from ara.graphs.experiment import build_experiment_graph
from ara.graphs.evolution import build_evolution_graph
from ara.nodes.supervisor import classify_intent_node, critic_node, replan_node

SUBGRAPHS = {
    "ingestion": build_ingestion_graph,
    "extraction": build_extraction_graph,
    "graph_update": build_graph_update_graph,
    "query": build_query_graph,
    "hypothesis": build_hypothesis_graph,
    "experiment": build_experiment_graph,
    "evolution": build_evolution_graph,
}

def build_main_graph(checkpointer: "BaseCheckpointSaver | None" = None):
    """
    Build the top‑level StateGraph.
    Nodes:
        - supervisor (classify_intent_node)
        - one node per compiled subgraph
        - critic (critic_node)
        - replan (replan_node)
    Edges:
        START → supervisor
        supervisor → subgraph (conditional on state['route'])
        subgraph → critic
        critic → END (or replan → supervisor if errors)
    """
    g = StateGraph(ARAState)

    g.add_node("supervisor", classify_intent_node)
    g.add_node("critic", critic_node)
    g.add_node("replan", replan_node)

    for name, builder in SUBGRAPHS.items():
        g.add_node(name, builder())

    g.set_entry_point("supervisor")

    # conditional edges from supervisor to subgraph based on route
    g.add_conditional_edges(
        "supervisor",
        lambda s: s.get("route", "end"),
        {name: name for name in SUBGRAPHS} | {"end": "END"},
    )

    # every subgraph goes to critic afterwards
    for name in SUBGRAPHS:
        g.add_edge(name, "critic")

    # critic decides: END or replan
    g.add_conditional_edges(
        "critic",
        lambda s: "replan" if s.get("needs_replan") else "END",
        {"replan": "replan", "END": "END"},
    )
    g.add_edge("replan", "supervisor")

    app = g.compile(
        checkpointer=checkpointer,
        interrupt_before=["graph_update"],  # human approval before KG writes
    )
    return app

# Singleton app with SQLite checkpointer
app = build_main_graph(SqliteSaver("checkpoints.sqlite"))

__all__ = ["build_main_graph", "app", "SUBGRAPHS"]
