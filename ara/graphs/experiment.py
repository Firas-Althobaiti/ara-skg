# File: ara/graphs/experiment.py
from langgraph import Graph
from ara.nodes.experiment import propose_experiment_node, validate_feasibility_node

def build_experiment_graph():
    """
    Experiment subgraph: START → propose → validate → END.
    Loops back to propose if validation fails (experiment_error present).
    """
    g = Graph()
    g.add_node("START", lambda: None)
    g.add_node("END", lambda: None)
    g.add_node("propose", propose_experiment_node)
    g.add_node("validate", validate_feasibility_node)

    g.add_edge("START", "propose")
    g.add_edge("propose", "validate")
    g.add_edge("validate", "END")

    g.add_conditional_edge(
        "validate",
        lambda state: state.get("experiment_error") is not None,
        target="propose",
    )
    return g

