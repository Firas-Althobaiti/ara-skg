# File: ara/nodes/experiment.py
from typing import Dict, Any, List
from ara.state import ARAState
from ara.schemas import ExperimentProposal
import asyncio

async def _mock_llm_propose(hypothesis_id: str, statement: str) -> ExperimentProposal:
    """Mock LLM call – in production use structured(llm, ExperimentProposal)."""
    return ExperimentProposal(
        id="exp_" + hypothesis_id,
        hypothesis_id=hypothesis_id,
        assay="cell_line_treatment",
        model_system="human_cells",
        controls=["vehicle"],
        readouts=["viability"],
        expected_outcomes=["increased_viability"],
        risks=["off_target_effects"],
        citations=["PMID:001"],
    )

async def propose_experiment_node(state: ARAState) -> Dict[str, Any]:
    """Generate an ExperimentProposal from the latest hypothesis."""
    hypotheses = state.get("hypotheses", [])
    if not hypotheses:
        state["experiment_error"] = "No hypothesis to base experiment on."
        return state
    hyp = hypotheses[-1]
    proposal = await _mock_llm_propose(hyp["id"], hyp["statement"])
    state["experiment"] = proposal.dict() if hasattr(proposal, "dict") else proposal
    return state

async def validate_feasibility_node(state: ARAState) -> Dict[str, Any]:
    """Basic feasibility checks: controls present, readouts measurable."""
    exp = state.get("experiment")
    if not exp:
        state["experiment_error"] = "No experiment proposal found."
        return state
    if not exp.get("controls") or not isinstance(exp["controls"], list) or len(exp["controls"]) == 0:
        state["experiment_error"] = "Experiment proposal missing controls."
        return state
    if not exp.get("readouts") or not isinstance(exp["readouts"], list) or len(exp["readouts"]) == 0:
        state["experiment_error"] = "Experiment proposal missing measurable readouts."
        return state
    return state

__all__ = ["propose_experiment_node", "validate_feasibility_node"]

