"""Experiment nodes: propose a design for the top hypothesis → validate."""

from __future__ import annotations

from typing import Any

from ara.schemas import ARAState, ExperimentProposal


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


async def _mock_llm_propose(hypothesis_id: str, statement: str) -> ExperimentProposal:
    """Mock LLM call – in production use structured(llm, ExperimentProposal)."""
    return ExperimentProposal(
        id="exp_" + hypothesis_id,
        hypothesis_id=hypothesis_id,
        assay="cell_line_treatment",
        model_system="human_cells",
        controls=["vehicle"],
        readouts=["viability", "target_phosphorylation"],
        expected_outcomes=["increased_viability"],
        risks=["off_target_effects"],
        citations=["PMID:001"],
    )


async def propose_experiment_node(state: ARAState) -> dict[str, Any]:
    """Generate one ExperimentProposal from the top-ranked hypothesis."""
    hypotheses = state.get("hypotheses", [])
    if not hypotheses:
        state["experiment_error"] = "No hypothesis to base experiment on."
        return {"experiment_error": state["experiment_error"]}
    hyp = hypotheses[0]  # hypotheses are ranked, so [0] is the best
    proposal = await _mock_llm_propose(_get(hyp, "id", ""), _get(hyp, "statement", ""))
    state["experiment"] = proposal.model_dump()
    state["experiments"] = state.get("experiments", []) + [proposal]
    return {"experiment": state["experiment"], "experiments": state["experiments"]}


async def validate_feasibility_node(state: ARAState) -> dict[str, Any]:
    """Basic feasibility checks: controls present, readouts measurable."""
    exp = state.get("experiment")
    if not exp:
        state["experiment_error"] = "No experiment proposal found."
        return {"experiment_error": state["experiment_error"]}
    controls = _get(exp, "controls", [])
    readouts = _get(exp, "readouts", [])
    if not controls or not isinstance(controls, list) or len(controls) == 0:
        state["experiment_error"] = "Experiment proposal missing controls."
        return {"experiment_error": state["experiment_error"]}
    if not readouts or not isinstance(readouts, list) or len(readouts) == 0:
        state["experiment_error"] = "Experiment proposal missing measurable readouts."
        return {"experiment_error": state["experiment_error"]}
    state.pop("experiment_error", None)
    return {}


# Alias matching the naming used by ``ara.nodes.__init__``.
validate_experiment_node = validate_feasibility_node


__all__ = ["propose_experiment_node", "validate_feasibility_node", "validate_experiment_node"]
