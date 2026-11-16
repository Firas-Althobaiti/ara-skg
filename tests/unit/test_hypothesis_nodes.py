import pytest
from ara.state import ARAState
from ara.nodes.hypothesis import (
    generate_hypotheses_node,
    ground_hypothesis_node,
    rank_hypotheses_node,
    critique_hypothesis_node,
)
from ara.schemas import Hypothesis

@pytest.mark.asyncio
async def test_generate_hypotheses_node():
    state = ARAState(
        task="test",
        intent="query",
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
    # add dummy valid triples for later grounding (not required here)
    state["valid_triples"] = [
        {
            "subject": {"name": "geneA", "type": "gene", "id": "geneA"},
            "predicate": "expresses",
            "object": {"name": "proteinX", "type": "protein", "id": "proteinX"},
            "confidence": 0.9,
            "provenance": {"paper_id": "PMID:001", "chunk_id": "c1", "span": 0, "extracted_by": "tester"},
        }
    ]
    result = await generate_hypotheses_node(state)
    assert "hypotheses" in result
    assert len(result["hypotheses"]) == 3
    for hyp in result["hypotheses"]:
        assert isinstance(hyp, Hypothesis)
        assert 0.0 <= hyp.novelty_score <= 1.0
        assert 0.0 <= hyp.plausibility_score <= 1.0

@pytest.mark.asyncio
async def test_ground_hypothesis_node():
    state = ARAState(
        task="test",
        intent="query",
        papers=[],
        chunks=[],
        extracted_triples=[],
        valid_triples=[
            {
                "subject": {"name": "geneA", "type": "gene", "id": "geneA"},
                "predicate": "expresses",
                "object": {"name": "proteinX", "type": "protein", "id": "proteinX"},
                "confidence": 0.9,
                "provenance": {"paper_id": "PMID:001", "chunk_id": "c1", "span": 0, "extracted_by": "tester"},
            }
        ],
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
    }
    # create three dummy hypotheses
    hyp1 = Hypothesis(
        id="h1",
        statement="h1",
        mechanism="test",
        entities=[],
        supporting=[],
        contradicting=[],
        novelty_score=0.5,
        plausibility_score=0.5,
        status="proposed",
    )
    hyp2 = Hypothesis(
        id="h2",
        statement="h2",
        mechanism="test",
        entities=[],
        supporting=[],
        contradicting=[],
        novelty_score=0.6,
        plausibility_score=0.5,
        status="proposed",
    )
    hyp3 = Hypothesis(
        id="h3",
        statement="h3",
        mechanism="test",
        entities=[],
        supporting=[],
        contradicting=[],
        novelty_score=0.4,
        plausibility_score=0.4,
        status="proposed",
    )
    state["hypotheses"] = [hyp1, hyp2, hyp3]
    result = await ground_hypothesis_node(state)
    # after grounding each hypothesis should have a 'supporting' list (may be empty)
    for hyp in result["hypotheses"]:
        assert hasattr(hyp, "supporting")
        assert isinstance(hyp.supporting, list)

@pytest.mark.asyncio
async def test_rank_hypotheses_node():
    state = ARAState(
        task="test",
        intent="query",
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
    # set hypotheses with varying scores
    hyp1 = Hypothesis(
        id="h1",
        statement="h1",
        mechanism="test",
        entities=[],
        supporting=[],
        contradicting=[],
        novelty_score=0.2,
        plausibility_score=0.5,
        status="proposed",
    )
    hyp2 = Hypothesis(
        id="h2",
        statement="h2",
        mechanism="test",
        entities=[],
        supporting=[],
        contradicting=[],
        novelty_score=0.6,
        plausibility_score=0.3,
        status="proposed",
    )
    hyp3 = Hypothesis(
        id="h3",
        statement="h3",
        mechanism="test",
        entities=[],
        supporting=[],
        contradicting=[],
        novelty_score=0.4,
        plausibility_score=0.6,
        status="proposed",
    )
    state["hypotheses"] = [hyp1, hyp2, hyp3]
    result = await rank_hypotheses_node(state)
    # after sorting, hyp2 (total 0.9) should be first
    assert result["hypotheses"][0].id == "h2"

@pytest.mark.asyncio
async def test_critique_hypothesis_node():
    state = ARAState(
        task="test",
        intent="query",
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
    # create two hypotheses: one with 2 supports, one with 1 support
    valid_triple1 = {
        "subject": {"name": "geneA", "type": "gene", "id": "geneA"},
        "predicate": "expresses",
        "object": {"name": "proteinX", "type": "protein", "id": "proteinX"},
        "confidence": 0.9,
        "provenance": {"paper_id": "PMID:001", "chunk_id": "c1", "span": 0, "extracted_by": "tester"},
    }
    valid_triple2 = {
        "subject": {"name": "geneB", "type": "gene", "id": "geneB"},
        "predicate": "binds",
        "object": {"name": "proteinY", "type": "protein", "id": "proteinY"},
        "confidence": 0.8,
        "provenance": {"paper_id": "PMID:001", "chunk_id": "c1", "span": 0, "extracted_by": "tester"},
    }
    hyp1 = Hypothesis(
        id="h1",
        statement="h1",
        mechanism="test",
        entities=[],
        supporting=[valid_triple1, valid_triple2],
        contradicting=[],
        novelty_score=0.6,
        plausibility_score=0.6,
        status="proposed",
    )
    hyp2 = Hypothesis(
        id="h2",
        statement="h2",
        mechanism="test",
        entities=[],
        supporting=[valid_triple1],  # only one support -> invalid
        contradicting=[],
        novelty_score=0.5,
        plausibility_score=0.5,
        status="proposed",
    )
    state["hypotheses"] = [hyp1, hyp2]
    result = await critique_hypothesis_node(state)
    # critique should say all are well supported because we filtered out the invalid one
    assert result["critique"] == "All hypotheses are well supported."
    # after critique, only the valid hypothesis should remain
    assert len(result["hypotheses"]) == 1
    assert result["hypotheses"][0].id == "h1"
