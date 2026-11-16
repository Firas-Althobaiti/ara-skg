from typing import Dict, Any, List
from ara.state import ARAState
from ara.schemas import ExperimentProposal, Hypothesis
from ara.config import get_settings
import asyncio

# ----------------------------------------------------------------------
# Dummy LLM call – in production this would call the LLM with the appropriate prompt.
# ----------------------------------------------------------------------
class DummyMessage:
    def __init__(self, content: str):
        self.content = content

async def _call_llm(prompt: str) -> List[dict]:
    """
    Mock LLM that returns a list of dictionaries representing an ExperimentProposal.
    """
    # Dummy data – in a real system this would be the LLM response.
    proposal = {
        "id": "exp_001",
        "hypothesis_id": "hyp_0",
        "assay": "cell_line_treatment",
        "model_system": "human_cells",
        "controls": ["vehicle"],
        "readouts": ["viability", "apoptosis"],
        "expected_outcomes": ["increased_viability", "reduced_apoptosis"],
        "risks": ["off_target_effects"],
        "citations": ["PMID:001", "arXiv:2001.001"],
    }
    return [proposal]

async def propose_experiment_node(state: ARAState) -> Dict[str, Any]:
    """Generate an ExperimentProposal from the latest hypothesis."""
    hypotheses = state.get("hypotheses", [])
    if not hypotheses:
        state["experiment_error"] = "No hypothesis available to propose an experiment."
        return state

    # Use the last hypothesis as the basis for the proposal.
    hyp = hypotheses[-1]
    proposal = await _call_llm(
        f"Propose an experiment for hypothesis {hyp.id}: {hyp.statement}"
    )
    state["experiment"] = proposal[0]  # take first item
    return state

async def validate_experiment_node(state: ARAState) -> Dict[str, Any]:
    """Validate that the ExperimentProposal contains all required fields."""
    exp = state.get("experiment")
    if not exp:
        state["experiment_error"] = "No experiment proposal found."
        return state

    required = ["assay", "model_system", "controls", "readouts",
                "expected_outcomes", "risks", "citations"]
    missing = [f for f in required if f not in exp or not exp[f]]
    if missing:
        state["experiment_error"] = f"Missing required fields: {missing}"
        return state

    # Basic sanity check – ensure controls and readouts are non‑empty lists.
    if not exp["controls"] or not exp["readouts"]:
        state["experiment_error"] = "Controls and readouts must be non‑empty lists."
        return state

    return state
