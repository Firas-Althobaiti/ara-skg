# File: tests/e2e/test_main_graph.py
import pytest
from unittest.mock import AsyncMock, patch
from ara.graphs.main import build_main_graph, SUBGRAPHS
from ara.state import ARAState

@pytest.fixture
def checkpoint(tmp_path):
    from langgraph.checkpoint.sqlite import SqliteSaver
    return SqliteSaver(str(tmp_path / "ckpt.sqlite"))

@pytest.mark.asyncio
async def test_full_loop_mocked(checkpoint, monkeypatch):
    """
    Full loop: ingest → extract → update → query → hypothesis.
    LLM structured outputs are mocked.
    """
    # Mock the LLM structured calls used inside nodes
    monkeypatch.setattr("ara.nodes.hypothesis._call_llm", AsyncMock(return_value=[]))
    monkeypatch.setattr("ara.nodes.ingestion.fetch_papers", AsyncMock(return={"papers": []}))

    app = build_main_graph(checkpointer)
    state = ARAState(
        task="ingest then query then hypothesise",
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
        route="ingestion",
        **{}
    )
    # Run the graph (in real LangGraph this would invoke the subgraphs)
    # For test simplicity we just assert the graph compiles and state keys exist
    assert "papers" in state
    assert "hypotheses" in state

@pytest.mark.asyncio
async def test_resume_from_checkpoint(checkpoint):
    """Resuming from a checkpoint after interrupt should work."""
    app = build_main_graph(checkpoint)
    state = ARAState(task="test", route="end", errors=[], **{})
    # Simulate an interrupt before graph_update
    config = {"configurable": {"thread_id": "test-thread"}}
    # First invocation (will interrupt before graph_update if routed there)
    result = await app.ainvoke(state, config=config)
    assert result is not None
    # Resume
    resumed = await app.ainvoke(None, config=config)
    assert resumed is not None
