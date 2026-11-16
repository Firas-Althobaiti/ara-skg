from .experiment import propose_experiment_node, validate_experiment_node
from .evolution import window_triples_node, detect_changes_node, summarize_evolution_node

async def classify_intent(state: ARAState) -> Dict[str, Any]:
    """
    Dispatch the current task to the appropriate subgraph node.
    This version supports:
        - generic tasks (default)
        - propose_experiment
        - validate_experiment
        - evolve (run the full evolution pipeline)
    """
    intent = state.get("intent", "").lower()
    if "experiment" in intent:
        # propose experiment
        state = await propose_experiment_node(state)
        return state
    if "validate_experiment" in intent:
        state = await validate_experiment_node(state)
        return state
    if "evolve" in intent:
        # run the full evolution pipeline
        state = await window_triples_node(state)
        state = await detect_changes_node(state)
        state = await summarize_evolution_node(state)
        return state
    # default: let the main graph decide (e.g., via subgraph dispatch)
    return state
