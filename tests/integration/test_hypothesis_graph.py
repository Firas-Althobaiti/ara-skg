import pytest

from ara.graphs.hypothesis import build_hypothesis_graph
from ara.nodes.hypothesis import (
    critique_hypothesis_node,
    generate_hypotheses_node,
    ground_hypothesis_node,
    rank_hypotheses_node,
)
from ara.schemas import ARAState


@pytest.mark.asyncio
async def test_hypothesis_graph_flow():
    # Build the graph (ensures imports work)
    build_hypothesis_graph()
    # Create a state with valid triples so that grounding can attach evidence
    valid_triple = {
        "subject": {"name": "geneA", "type": "gene", "id": "geneA"},
        "predicate": "expresses",
        "object": {"name": "proteinX", "type": "protein", "id": "proteinX"},
        "confidence": 0.9,
        "provenance": {
            "paper_id": "PMID:001",
            "chunk_id": "c1",
            "span": 0,
            "extracted_by": "tester",
        },
    }
    valid_triple2 = {
        "subject": {"name": "proteinX", "type": "protein", "id": "proteinX"},
        "predicate": "binds",
        "object": {"name": "proteinY", "type": "protein", "id": "proteinY"},
        "confidence": 0.8,
        "provenance": {
            "paper_id": "PMID:001",
            "chunk_id": "c1",
            "span": 0,
            "extracted_by": "tester",
        },
    }
    state = ARAState(
        task="test",
        intent="query",
        papers=[],
        chunks=[],
        extracted_triples=[],
        valid_triples=[valid_triple, valid_triple2],
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
    # Execute the nodes sequentially, merging each partial update into the state
    for node in (
        generate_hypotheses_node,
        ground_hypothesis_node,
        rank_hypotheses_node,
        critique_hypothesis_node,
    ):
        state.update(await node(state))

    # Verify that we ended with at least one valid hypothesis and a critique message
    assert len(state["hypotheses"]) > 0
    assert "critique" in state
    assert isinstance(state["critique"], str)
