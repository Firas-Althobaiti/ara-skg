import asyncio
from ara.state import ARAState
from ara.graphs.evolution import build_evolution_graph
from ara.nodes.evolution import (
    window_triples_node,
    detect_changes_node,
    summarize_evolution_node,
)

@pytest.mark.asyncio
async def test_evolution_graph_flow():
    # Build the evolution graph (ensures imports work)
    graph = build_evolution_graph()

    # Create a minimal state with some valid triples for current and previous windows
    state = ARAState(
        task="test",
        intent="evolve",
        papers=[],
        chunks=[],
        extracted_triples=[],
        valid_triples=[
            # current window triples
            {
                "subject": {"name": "geneA", "type": "gene", "id": "geneA"},
                "predicate": "expresses",
                "object": {"name": "proteinX", "type": "protein", "id": "proteinX"},
                "confidence": 0.9,
                "provenance": {"paper_id": "PMID:001", "chunk_id": "c1", "span": 0, "extracted_by": "tester"},
            },
            {
                "subject": {"name": "proteinX", "type": "protein", "id": "proteinX"},
                "predicate": "binds",
                "object": {"name": "proteinY", "type": "protein", "id": "proteinY"},
                "confidence": 0.8,
                "provenance": {"paper_id": "PMID:001", "chunk_id": "c1", "span": 0, "extracted_by": "tester"},
            },
        ],
        prev_valid_triples=[],  # previous window empty for this test
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

    # Execute the evolution pipeline
    state = await window_triples_node(state)
    state = await detect_changes_node(state)
    state = await summarize_evolution_node(state)

    # Verify that a report was produced
    assert "evolution_report" in state
    assert isinstance(state["evolution_report"], str)
    # At least one event should be detected (emerging, fading, etc.)
    events = state.get("evolution_events", [])
    assert len(events) > 0
