import asyncio
from ara.state import ARAState
from ara.graphs.query import build_query_graph
from ara.nodes.query import (
    classify_query_node,
    nl2cypher_node,
    guard_cypher_node,
    run_cypher_node,
    synthesize_answer_node,
)

@pytest.mark.asyncio
async def test_query_graph_flow():
    # Build the graph (ensures imports work)
    graph = build_query_graph()
    # Create a minimal state with a query intent
    state = ARAState(
        task="list all genes",
        intent="query",   # will be set by classify node
        papers=[],
        chunks=[],
        extracted_triples=[],
        valid_triples=[],
        kg_delta=[],
        retrieved_subgraph=[],
        hypotheses=[],
        experiments=[],
        evolution_report="",
        critique="",
        errors=[],
        next_step=None,
        provenance={},
        budget=None,
        cypher="",
        params={},
        run_result={"result": [], "runtime": 0.0},
        final_answer="",
    )
    # Execute the nodes in order (simulating the graph)
    state = await classify_query_node(state)
    state = await nl2cypher_node(state)
    state = await guard_cypher_node(state)
    state = await run_cypher_node(state)
    state = await synthesize_answer_node(state)

    # Verify that a final answer was produced
    assert "final_answer" in state
    assert isinstance(state["final_answer"], str)
