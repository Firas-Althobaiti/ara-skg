import pytest
from ara.state import ARAState
from ara.nodes.query import (
    classify_query_node,
    nl2cypher_node,
    guard_cypher_node,
    run_cypher_node,
    synthesize_answer_node,
)

@pytest.mark.asyncio
async def test_classify_query():
    state = ARAState(task="what is gene A?")
    state = await classify_query_node(state)
    assert state["intent"] == "query"

    state = ARAState(task="list all papers")
    state = await classify_query_node(state)
    assert state["intent"] == "generic"


@pytest.mark.asyncio
async def test_nl2cypher_node():
    state = ARAState(task="list all entities", intent="generic")
    state = await nl2cypher_node(state)
    assert state["cypher"] == ""  # no pattern for generic intent

    state = ARAState(task="list all entities", intent="query")
    state = await nl2cypher_node(state)
    assert "MATCH" in state["cypher"]
    assert state["params"] == {}


@pytest.mark.asyncio
async def test_guard_cypher_node_allow():
    state = ARAState(
        task="list entities",
        intent="query",
        cypher="MATCH (n) RETURN n.name",
        params={},
    )
    state = await guard_cypher_node(state)
    assert state.get("error") is None


@pytest.mark.asyncio
async def test_guard_cypher_node_reject():
    state = ARAState(
        task="list entities",
        intent="query",
        cypher="CREATE (n) RETURN n",
        params={},
    )
    state = await guard_cypher_node(state)
    assert state["error"] == "write operation not allowed"


@pytest.mark.asyncio
async def test_run_cypher_node_success():
    # mock client
    class MockClient:
        async def query_cypher(self, cypher, params):
            return [{"name": "GeneA", "id": "1"}]
    mock_client = MockClient()
    # patch get_settings to return a client with this mock
    class DummySettings:
        def get_settings(cls):
            class Inner:
                client = MockClient()
            return Inner()
        return Inner()
    # patch get_settings
    import ara.config
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(ara.config, "get_settings", lambda: DummySettings().get_settings())
    state = ARAState(
        task="test query",
        intent="query",
        cypher="MATCH (n) RETURN n.name AS name, n.id AS id",
        params={},
    )
    state = await run_cypher_node(state)
    assert "run_result" in state
    assert state["run_result"]["result"] == [{"name": "GeneA", "id": "1"}]
    assert isinstance(state["run_result"]["runtime"], float)


@pytest.mark.asyncio
async def test_synthesize_answer_node():
    state = ARAState(
        task="explain gene A",
        intent="query",
        run_result={"result": [{"name": "GeneA", "description": "Gene A is a transcription factor"}]},
        final_answer="",
    )
    state = await synthesize_answer_node(state)
    assert state["final_answer"] == "Found: GeneA: Gene A is a transcription factor"
