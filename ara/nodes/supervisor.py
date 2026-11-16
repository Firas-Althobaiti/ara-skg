from typing import Dict, Any
from ara.state import ARAState

async def classify_intent(state: ARAState) -> Dict[str, Any]:
    """
    Dispatch the current task to the appropriate subgraph node.
    """
    return state

async def critic_check(state: ARAState) -> Dict[str, Any]:
    """
    Final grounding validation before committing any changes.
    """
    return state

async def replan_task(state: ARAState) -> Dict[str, Any]:
    """
    Re‑evaluate the plan if the previous step failed or if new information arrived.
    """
    return state
