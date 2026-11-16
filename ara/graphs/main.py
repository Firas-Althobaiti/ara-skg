# File: ara/graphs/main.py
from langgraph import Graph
from ara.state import ARAState
from ara.nodes.supervisor import classify_intent

def build_main_graph(checkpointer: "BaseCheckpointSaver | None" = None) -> "Graph":
    """
    Build the top‑level graph that ties all subgraphs together.
    The graph contains a single supervisor node that decides which
    subgraph to invoke based on the current intent stored in ARAState.
    """
    g = Graph()
    # dummy start and end nodes required by LangGraph
    g.add_node("START", lambda: None)
    g.add_node("END", lambda: None)

    # supervisor node – decides which subgraph to run
    g.add_node("supervisor", classify_intent)

    # edges
    g.add_edge("START", "supervisor")
    g.add_edge("supervisor", "END")

    # optional: if the intent indicates a specific subgraph,
    # we can route directly to that subgraph's start node.
    # For simplicity we let the supervisor node decide which node to call
    # by setting a temporary attribute in the state (e.g. state["node"]).
    # The subgraph nodes are already defined as separate callable nodes,
    # so the supervisor can call them directly.
    return g

