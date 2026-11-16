from typing import Dict, Any
from ara.state import ARAState

async def classify_intent(state: ARAState) -> Dict[str, Any]:
    """
    Dispatch the current task to the appropriate subgraph node.
    Supported intents:
        - "experiment"      → run the experiment flow (propose → validate)
        - "validate_experiment" → run validation only
        - "evolve"        → run the full evolution pipeline (window → detect → summarize)
        - any other intent → let the main graph decide (default behaviour)
    """
    intent = state.get("intent", "").lower()
    if "experiment" in intent:
        # Run the full experiment flow (propose → validate)
        state = await propose_experiment_node(state)
        state = await validate_experiment_node(state)
        return state
    if "validate_experiment" in intent:
        state = await validate_experiment_node(state)
        return state
    if "evolve" in intent:
        # Run the evolution pipeline
        state = await window_triples_node(state)
        state = await detect_changes_node(state)
        state = await summarize_evolution_node(state)
        return state
    # default: let the main graph decide (e.g., via subgraph dispatch)
    return state
