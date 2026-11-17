from langgraph import Graph

from ara.nodes.graph_update import (
    ensure_schema_node,
    resolve_triples_node,
    rollback_on_error,
    upsert_kg_node,
)


def build_graph_update_graph():
    """
    Build the Graph Update subgraph.
    Nodes:
        - resolve_triples
        - ensure_schema
        - upsert_kg
        - rollback_on_error (conditional)
    Edges enforce ordering and error handling.
    """
    g = Graph()
    # dummy start/end nodes required by LangGraph
    g.add_node("START", lambda: None)
    g.add_node("END", lambda: None)

    # real processing nodes
    g.add_node("resolve_triples", resolve_triples_node)
    g.add_node("ensure_schema", ensure_schema_node)
    g.add_node("upsert_kg", upsert_kg_node)
    g.add_node("rollback_on_error", rollback_on_error)

    # wiring
    g.add_edge("START", "resolve_triples")
    g.add_edge("resolve_triples", "ensure_schema")
    g.add_edge("ensure_schema", "upsert_kg")
    # conditional: if upsert fails (state has errors), go to rollback, else to END
    g.add_conditional_edge(
        "upsert_kg",
        lambda state: bool(state.get("errors", [])),
        target="rollback_on_error",
    )
    g.add_edge("rollback_on_error", "END")
    g.add_edge("upsert_kg", "END")  # success path

    return g
