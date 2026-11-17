from langgraph import Graph

from ara.nodes.hypothesis import (
    critique_hypothesis_node,
    generate_hypotheses_node,
    ground_hypothesis_node,
    rank_hypotheses_node,
)


def build_hypothesis_graph():
    """
    Build the Hypothesis subgraph.
    Nodes:
        - generate   – generate_hypotheses_node
        - ground     – ground_hypothesis_node
        - rank       – rank_hypotheses_node
        - critique   – critique_hypothesis_node
    Edges enforce linear flow; a conditional edge allows looping back to
    ``generate if the critique reports an error (e.g., no valid hypotheses).
    """
    g = Graph()
    # dummy start/end nodes required by LangGraph
    g.add_node("START", lambda: None)
    g.add_node("END", lambda: None)

    # real processing nodes
    g.add_node("generate", generate_hypotheses_node)
    g.add_node("ground", ground_hypothesis_node)
    g.add_node("rank", rank_hypotheses_node)
    g.add_node("critique", critique_hypothesis_node)

    # wiring
    g.add_edge("START", "generate")
    g.add_edge("generate", "ground")
    g.add_edge("ground", "rank")
    g.add_edge("rank", "critique")
    g.add_edge("critique", "END")

    # conditional loop back to generate if critique reports an error
    g.add_conditional_edge(
        "critique",
        lambda state: state.get("critique_error") is not None,
        target="generate",
    )
    return g
