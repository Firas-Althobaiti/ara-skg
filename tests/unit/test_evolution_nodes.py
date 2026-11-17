# File: tests/unit/test_evolution_nodes.py
import pytest
from ara.state import ARAState

from ara.nodes.evolution import detect_changes_node


@pytest.mark.asyncio
async def test_detect_changes_fading_event():
    """Synthetic triples with a known drop → assert a `fading` event is detected."""
    prev = [
        {
            "subject": {"id": "geneA", "name": "GeneA", "type": "gene"},
            "predicate": "expresses",
            "object": {"id": "proteinX", "name": "ProteinX", "type": "protein"},
            "confidence": 0.9,
            "provenance": {
                "paper_id": "PMID:1",
                "chunk_id": "c1",
                "span": 0,
                "extracted_by": "tester",
            },
        }
    ]
    current = []  # geneA dropped
    state = ARAState(
        task="test",
        intent="evolve",
        papers=[],
        chunks=[],
        extracted_triples=[],
        valid_triples=current,
        prev_valid_triples=prev,
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
    result = await detect_changes_node(state)
    events = result.get("evolution_events", [])
    assert any(e["change_type"] == "fading" and e["entity_id"] == "geneA" for e in events)
