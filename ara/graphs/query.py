from langgraph import Graph

from ara.nodes.query import (
    classify_query_node,
    guard_cypher_node,
    nl2cypher_node,
    run_cypher_node,
    synthesize_answer_node,
)


def build_query_graph():
    """
    Build the Query subgraph.
    Nodes:
        - classify_query
        - nl2cypher
        - guard_cypher
        - run_cypher
        - synthesize_answer
    Edges enforce linear flow with a guard check.
    """
    g = Graph()
    # dummy start/end nodes required by LangGraph
    g.add_node("START", lambda: None)
    g.add_node("END", lambda: None)

    # real processing nodes
    g.add_node("classify_query", classify_query_node)
    g.add_node("nl2cypher", nl2cypher_node)
    g.add_node("guard_cypher", guard_cypher_node)
    g.add_node("run_cypher", run_cypher_node)
    g.add_node("synthesize_answer", synthesize_answer_node)

    # wiring
    g.add_edge("START", "classify_query")
    g.add_edge("classify_query", "nl2cypher")
    g.add_edge("nl2cypher", "guard_cypher")
    g.add_edge("guard_cypher", "run_cypher")
    g.add_edge("run_cypher", "synthesize_answer")
    g.add_edge("synthesize_answer", "END")

    # conditional guard: if guard_cypher reports an error, go to END (fail)
    g.add_conditional_edge(
        "guard_cypher",
        lambda state: state.get("error") is not None,
        target="END",
    )
    return g
