from langgraph import Graph
from ara.state import ARAState
from ara.nodes.experiment import (
    propose_experiment_node,
    validate_experiment_node,
)

def build_experiment_graph():
    """
    Build the Experiment subgraph.
    Nodes:
        - propose   – propose_experiment_node
        - validate  – validate_experiment_node
    Edges enforce linear flow; a conditional edge allows looping back to
    ``propose if validation fails (state contains ``experiment_error).
    """
    g = Graph()
    g.add_node("START", lambda: None)
    g.add_node("END", lambda: None)

    g.add_node("propose", propose_experiment_node)
    g.add_node("validate", validate_experiment_node)

    g.add_edge("START", "propose")
    g.add_edge("propose", "validate")
    g.add_edge("validate", "END")

    # Conditional loop back to propose if validation fails
    g.add_conditional_edge(
        "validate",
        lambda state: state.get("experiment_error") is not None,
        target="propose",
    )
    return g
