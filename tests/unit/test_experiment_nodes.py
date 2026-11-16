import pytest
from ara.state import ARAState
from ara.nodes.experiment import (
    propose_experiment_node,
    validate_experiment_node,
)

@pytest.mark.asyncio
async def test_propose_experiment_node():
    state = ARAState(
        task="test",
        intent="propose_experiment",
        papers=[],
        chunks=[],
        extracted_triples=[],
        valid_triples=[],
        hypotheses=[],
        errors=[],
        next_step=None,
        provenance={},
        budget=None,
        cypher="",
        params={},
        run_result={"result": [], "runtime": 0.0},
        final_answer="",
        **{},
    )
    # add a dummy hypothesis for context
    from ara.schemas import Hypothesis
    hyp = Hypothesis(
        id="hyp_0",
        statement="GeneA activates ProteinX",
        mechanism="activation",
        entities=[],
        supporting=[],
        contradicting=[],
        novelty_score=0.6,
        plausibility_score=0.7,
        status="proposed",
    )
    state["hypotheses"] = [hyp]
    result = await propose_experiment_node(state)
    assert "experiment" in result
    assert result["experiment"]["id"] == "exp_001"

@pytest.mark.asyncio
async def test_validate_experiment_node_success():
    state = ARAState(
        task="test",
        intent="validate_experiment",
        papers=[],
        chunks=[],
        extracted_triples=[],
        valid_triples=[],
        hypotheses=[],
        errors=[],
        next_step=None,
        provenance={},
        budget=None,
        cypher="",
        params={},
        run_result={"result": [], "runtime": 0.0},
        final_answer="",
        **{},
    )
    # add a valid experiment proposal
    state["experiment"] = {
        "id": "exp_001",
        "hypothesis_id": "hyp_0",
        "assay": "cell_line_treatment",
        "model_system": "human_cells",
        "controls": ["vehicle"],
        "readouts": ["viability", "apoptosis"],
        "expected_outcomes": ["increased_viability", "reduced_apoptosis"],
        "risks": ["off_target_effects"],
        "citations": ["PMID:001"],
    )
    result = await validate_experiment_node(state)
    assert "experiment_error" not in result

@pytest.mark.asyncio
async def test_validate_experiment_node_failure():
    state = ARAState(
        task="test",
        intent="validate_experiment",
        papers=[],
        chunks=[],
        extracted_triples=[],
        valid_triples=[],
        hypotheses=[],
        errors=[],
        next_step=None,
        provenance={},
        budget=None,
        cypher="",
        params={},
        run_result={"result": [], "runtime": 0.0},
        final_answer="",
        **{},
    )
    # missing required field
    state["experiment"] = {
        "id": "exp_001",
        "hypothesis_id": "hyp_0",
        "assay": "cell_line_treatment",
        "model_system": "human_cells",
        "controls": [],  # missing readouts
        "readouts": ["viability"],
        "expected_outcomes": ["increased_viability"],
        "risks": ["off_target_effects"],
        "citations": ["PMID:001"],
    }
    result = await validate_experiment_node(state)
    assert "experiment_error" in result
    assert "Missing required fields" in result["experiment_error"]
