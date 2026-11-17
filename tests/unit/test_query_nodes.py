import pytest
from ara.state import ARAState

from ara.nodes.query import (
    classify_query_node,
    guard_cypher_node,
    nl2cypher_node,
    run_cypher_node,
    synthesize_answer_node,
)


@pytest.mark.asyncio
async def test_classify_query() -> None:
    state: ARAState = {"task": "what is gene A?"}
    result = await classify_query_node(state)
    assert result["intent"] == "query"

    state2: ARAState = {"task": "list all papers"}
    result2 = await classify_query_node(state2)
    assert result2["intent"] == "generic"


@pytest.mark.asyncio
async def test_nl2cypher_node() -> None:
    state: ARAState = {"task": "list all entities", "intent": "generic"}
    result = await nl2cypher_node(state)
    assert result["cypher"] == ""

    state2: ARAState = {"task": "list all entities", "intent": "query"}
    result2 = await nl2cypher_node(state2)
    assert "MATCH" in result2["cypher"]
    assert result2["params"] == {}


@pytest.mark.asyncio
async def test_guard_cypher_node_allow() -> None:
    state: ARAState = {
        "task": "list entities",
        "intent": "query",
        "cypher": "MATCH (n) RETURN n.name",
        "params": {},
    }
    result = await guard_cypher_node(state)
    assert result.get("error") is None


@pytest.mark.asyncio
async def test_guard_cypher_node_reject() -> None:
    state: ARAState = {
        "task": "list entities",
        "intent": "query",
        "cypher": "CREATE (n) RETURN n",
        "params": {},
    }
    result = await guard_cypher_node(state)
    assert result["error"] == "write operation not allowed"


@pytest.mark.asyncio
async def test_run_cypher_node_success(monkeypatch: pytest.MonkeyPatch) -> None:
    class MockClient:
        async def query_cypher(self, cypher: str, params: dict) -> list[dict]:
            return [{"name": "GeneA", "id": "1"}]

    class MockSettings:
        client = MockClient()

    # Patch get_settings where it is used in the query node
    monkeypatch.setattr("ara.nodes.query.get_settings", lambda: MockSettings())

    state: ARAState = {
        "task": "test query",
        "intent": "query",
        "cypher": "MATCH (n) RETURN n.name AS name, n.id AS id",
        "params": {},
    }
    result = await run_cypher_node(state)
    assert "run_result" in result
    assert result["run_result"]["result"] == [{"name": "GeneA", "id": "1"}]
    assert isinstance(result["run_result"]["runtime"], float)


@pytest.mark.asyncio
async def test_synthesize_answer_node() -> None:
    state: ARAState = {
        "task": "explain gene A",
        "intent": "query",
        "run_result": {
            "result": [{"name": "GeneA", "description": "Gene A is a transcription factor"}],
            "runtime": 0.1,
        },
        "final_answer": "",
    }
    result = await synthesize_answer_node(state)
    assert result["final_answer"] == "Found: GeneA: Gene A is a transcription factor"
