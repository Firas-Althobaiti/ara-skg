import pytest
from ara.state import ARAState

from ara.nodes.hypothesis import (
    critique_hypothesis_node,
    generate_hypotheses_node,
    ground_hypothesis_node,
    rank_hypotheses_node,
)
from ara.schemas import EntityRef, Hypothesis, Provenance, Triple


@pytest.mark.asyncio
async def test_generate_hypotheses_node() -> None:
    state: ARAState = {
        "task": "test",
        "intent": "query",
        "papers": [],
        "chunks": [],
        "extracted_triples": [],
        "valid_triples": [
            Triple(
                subject=EntityRef(name="geneA", type="gene", id="geneA"),
                predicate="expresses",
                object=EntityRef(name="proteinX", type="protein", id="proteinX"),
                confidence=0.9,
                provenance=Provenance(
                    paper_id="PMID:001", chunk_id="c1", span=0, extracted_by="tester"
                ),
            )
        ],
        "hypotheses": [],
        "errors": [],
        "next_step": None,
        "provenance": {},
        "budget": None,
        "cypher": "",
        "params": {},
        "run_result": {"result": [], "runtime": 0.0},
        "final_answer": "",
    }
    result = await generate_hypotheses_node(state)
    assert "hypotheses" in result
    assert len(result["hypotheses"]) == 3
    for hyp in result["hypotheses"]:
        assert isinstance(hyp, Hypothesis)
        assert 0.0 <= hyp.novelty_score <= 1.0
        assert 0.0 <= hyp.plausibility_score <= 1.0


@pytest.mark.asyncio
async def test_ground_hypothesis_node() -> None:
    state: ARAState = {
        "task": "test",
        "intent": "query",
        "papers": [],
        "chunks": [],
        "extracted_triples": [],
        "valid_triples": [
            Triple(
                subject=EntityRef(name="geneA", type="gene", id="geneA"),
                predicate="expresses",
                object=EntityRef(name="proteinX", type="protein", id="proteinX"),
                confidence=0.9,
                provenance=Provenance(
                    paper_id="PMID:001", chunk_id="c1", span=0, extracted_by="tester"
                ),
            )
        ],
        "hypotheses": [
            Hypothesis(
                id="h1",
                statement="h1",
                mechanism="test",
                entities=[],
                supporting=[],
                contradicting=[],
                novelty_score=0.5,
                plausibility_score=0.5,
                status="proposed",
            ),
            Hypothesis(
                id="h2",
                statement="h2",
                mechanism="test",
                entities=[],
                supporting=[],
                contradicting=[],
                novelty_score=0.6,
                plausibility_score=0.5,
                status="proposed",
            ),
            Hypothesis(
                id="h3",
                statement="h3",
                mechanism="test",
                entities=[],
                supporting=[],
                contradicting=[],
                novelty_score=0.4,
                plausibility_score=0.4,
                status="proposed",
            ),
        ],
        "errors": [],
        "next_step": None,
        "provenance": {},
        "budget": None,
        "cypher": "",
        "params": {},
        "run_result": {"result": [], "runtime": 0.0},
        "final_answer": "",
    }
    result = await ground_hypothesis_node(state)
    for hyp in result["hypotheses"]:
        assert hasattr(hyp, "supporting")
        assert isinstance(hyp.supporting, list)


@pytest.mark.asyncio
async def test_rank_hypotheses_node() -> None:
    state: ARAState = {
        "task": "test",
        "intent": "query",
        "papers": [],
        "chunks": [],
        "extracted_triples": [],
        "valid_triples": [],
        "hypotheses": [
            Hypothesis(
                id="h1",
                statement="h1",
                mechanism="test",
                entities=[],
                supporting=[],
                contradicting=[],
                novelty_score=0.2,
                plausibility_score=0.5,
                status="proposed",
            ),
            Hypothesis(
                id="h2",
                statement="h2",
                mechanism="test",
                entities=[],
                supporting=[],
                contradicting=[],
                novelty_score=0.6,
                plausibility_score=0.3,
                status="proposed",
            ),
            Hypothesis(
                id="h3",
                statement="h3",
                mechanism="test",
                entities=[],
                supporting=[],
                contradicting=[],
                novelty_score=0.4,
                plausibility_score=0.6,
                status="proposed",
            ),
        ],
        "errors": [],
        "next_step": None,
        "provenance": {},
        "budget": None,
        "cypher": "",
        "params": {},
        "run_result": {"result": [], "runtime": 0.0},
        "final_answer": "",
    }
    result = await rank_hypotheses_node(state)
    assert result["hypotheses"][0].id == "h2"


@pytest.mark.asyncio
async def test_critique_hypothesis_node() -> None:
    valid_triple1 = Triple(
        subject=EntityRef(name="geneA", type="gene", id="geneA"),
        predicate="expresses",
        object=EntityRef(name="proteinX", type="protein", id="proteinX"),
        confidence=0.9,
        provenance=Provenance(paper_id="PMID:001", chunk_id="c1", span=0, extracted_by="tester"),
    )
    valid_triple2 = Triple(
        subject=EntityRef(name="geneB", type="gene", id="geneB"),
        predicate="binds",
        object=EntityRef(name="proteinY", type="protein", id="proteinY"),
        confidence=0.8,
        provenance=Provenance(paper_id="PMID:001", chunk_id="c1", span=0, extracted_by="tester"),
    )
    state: ARAState = {
        "task": "test",
        "intent": "query",
        "papers": [],
        "chunks": [],
        "extracted_triples": [],
        "valid_triples": [valid_triple1, valid_triple2],
        "hypotheses": [
            Hypothesis(
                id="h1",
                statement="h1",
                mechanism="test",
                entities=[],
                supporting=[valid_triple1, valid_triple2],
                contradicting=[],
                novelty_score=0.6,
                plausibility_score=0.6,
                status="proposed",
            ),
            Hypothesis(
                id="h2",
                statement="h2",
                mechanism="test",
                entities=[],
                supporting=[valid_triple1],
                contradicting=[],
                novelty_score=0.5,
                plausibility_score=0.5,
                status="proposed",
            ),
        ],
        "errors": [],
        "next_step": None,
        "provenance": {},
        "budget": None,
        "cypher": "",
        "params": {},
        "run_result": {"result": [], "runtime": 0.0},
        "final_answer": "",
    }
    result = await critique_hypothesis_node(state)
    assert result["critique"] == "All hypotheses are well supported."
    assert len(result["hypotheses"]) == 1
    assert result["hypotheses"][0].id == "h1"
