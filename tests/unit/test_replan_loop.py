"""Regression test for the bounded replan loop (issue #8).

Before the fix, ``critic → replan → supervisor`` cycled until LangGraph
raised ``GraphRecursionError``. Now the loop is capped at
``MAX_REPLANS = 3`` and the graph ends at END with all errors preserved.
"""

from __future__ import annotations

from typing import Any

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from ara.graphs import main as main_module
from ara.graphs.main import build_main_graph
from ara.nodes.supervisor import MAX_REPLANS
from ara.schemas import ARAState


@pytest.mark.asyncio
async def test_persistent_failure_ends_at_end_with_errors_preserved(monkeypatch) -> None:
    """A subgraph that always errors must not crash the graph.

    Expected: 1 initial run + MAX_REPLANS replans = 4 executions → 4 error
    messages preserved, ``replan_count == MAX_REPLANS``, graph reaches END.
    """

    async def failing_node(state: ARAState) -> dict[str, Any]:
        errors = list(state.get("errors", []))
        errors.append(f"boom-{len(errors) + 1}")
        return {"errors": errors}

    sub = StateGraph(ARAState)
    sub.add_node("boom", failing_node)
    sub.add_edge(START, "boom")
    sub.add_edge("boom", END)
    monkeypatch.setitem(main_module.SUBGRAPHS, "ingestion", lambda: sub.compile())

    app = build_main_graph(MemorySaver())
    config = {"configurable": {"thread_id": "replan-loop-test"}}
    result = await app.ainvoke({"task": "ingest pubmed brca1", "errors": []}, config=config)

    assert result["replan_count"] == MAX_REPLANS == 3
    assert result["needs_replan"] is False  # critic stopped requesting replans → END
    assert result["errors"] == ["boom-1", "boom-2", "boom-3", "boom-4"]


@pytest.mark.asyncio
async def test_successful_run_never_replans(monkeypatch) -> None:
    """Sanity: a subgraph that succeeds ends immediately with no replans."""

    async def ok_node(state: ARAState) -> dict[str, Any]:
        return {"final_answer": "done"}

    sub = StateGraph(ARAState)
    sub.add_node("ok", ok_node)
    sub.add_edge(START, "ok")
    sub.add_edge("ok", END)
    monkeypatch.setitem(main_module.SUBGRAPHS, "query", lambda: sub.compile())

    app = build_main_graph(MemorySaver())
    config = {"configurable": {"thread_id": "no-replan-test"}}
    result = await app.ainvoke({"task": "query anything?", "errors": []}, config=config)

    assert result.get("replan_count", 0) == 0
    assert result["needs_replan"] is False
    assert result["final_answer"] == "done"
