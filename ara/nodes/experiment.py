from typing import Dict, Any
from ara.state import ARAState

async def propose_experiment(state: ARAState) -> Dict[str, Any]:
    """
    Given a hypothesis, propose an experimental design.
    Returns an ExperimentProposal object.
    """
    return state

async def validate_experiment(state: ARAState) -> Dict[str, Any]:
    """
    Basic feasibility checks (controls, measurable readouts, etc.).
    """
    return state
