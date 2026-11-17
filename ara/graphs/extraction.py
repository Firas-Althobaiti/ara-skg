from langgraph import Graph

from ara.nodes.extraction import (
    extract_entities_node,
    extract_relations_node,
    link_entities_node,
    validate_triples_node,
)


def build_extraction_graph():
    """
    Build a LangGraph subgraph for extraction.
    Nodes:
        - extract_entities
        - extract_relations
        - link_entities
        - validate_triples
    Edges enforce the linear flow.
    """
    g = Graph()
    # dummy start/end nodes required by LangGraph
    g.add_node("START", lambda: None)
    g.add_node("END", lambda: None)

    # real processing nodes
    g.add_node("extract_entities", extract_entities_node)
    g.add_node("extract_relations", extract_relations_node)
    g.add_node("link_entities", link_entities_node)
    g.add_node("validate_triples", validate_triples_node)

    # wiring
    g.add_edge("START", "extract_entities")
    g.add_edge("extract_entities", "extract_relations")
    g.add_edge("extract_relations", "link_entities")
    g.add_edge("link_entities", "validate_triples")
    g.add_edge("validate_triples", "END")
    return g
