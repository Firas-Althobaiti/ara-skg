# File: ara/graphs/evolution.py
from langgraph import Graph
from ara.nodes.evolution import (
    window_triples_node,
    detect_changes_node,
    summarize_evolution_node,
)

def build_evolution_graph():
    """
    Evolution subgraph: START → window → detect → summarize → END.
    Loops back to window if an evolution_error is present.
    """
    g = Graph()
    g.add_node("START", lambda: None)
    g.add_node("END", lambda: None)
    g.add_node("window", window_triples_node)
    g.add_node("detect", detect_changes_node)
    g.add_node("summarize", summarize_evolution_node)

    g.add_edge("START", "window")
    g.add_edge("window", "detect")
    g.add_edge("detect", "summarize")
    g.add_edge("summarize", "END")

    g.add_conditional_edge(
        "detect",
        lambda state: state.get("evolution_error") is not None,
        target="window",
    )
    return g

