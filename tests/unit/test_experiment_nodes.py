# File: tests/unit/test_experiment_nodes.py
import pytest
from ara.state import ARAState

from ara.nodes.experiment import propose_experiment_node, validate_feasibility_node


@pytest.mark.asyncio
async def test_validate_feasibility_rejects_missing_controls():
    state = ARAState(
        task="test",
        intent="experiment",
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
    # proposal missing controls
    state["experiment"] = {
        "id": "exp_1",
        "hypothesis_id": "hyp_1",
        "assay": "assay",
        "model_system": "cells",
        "controls": [],  # ← missing
        "readouts": ["viability"],
        "expected_outcomes": ["x"],
        "risks": [],
        "citations": [],
    }
    result = await validate_feasibility_node(state)
    assert "experiment_error" in result
    assert "controls" in result["experiment_error"]


@pytest.mark.asyncio
async def test_propose_experiment_node_success():
    state = ARAState(
        task="test",
        intent="experiment",
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
    hyp = {
        "id": "hyp_0",
        "statement": "GeneA activates ProteinX",
        "mechanism": "activation",
        "entities": [],
        "supporting": [],
        "contradicting": [],
        "novelty_score": 0.6,
        "plausibility_score": 0.7,
        "status": "proposed",
    }
    state["hypotheses"] = [hyp]
    result = await propose_experiment_node(state)
    assert "experiment" in result
    assert result["experiment"]["hypothesis_id"] == "hyp_0"
