"""E2E test that actually exercises interrupt_before=["graph_update"] (issue #17).

A task routing to graph_update must HALT before the subgraph runs (KG still
empty), then resume on a second ainvoke with the same thread and write the
triples. A non-graph_update route must NOT halt.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from langgraph.checkpoint.memory import MemorySaver

from ara.config import get_settings
from ara.graphs.main import build_main_graph
from ara.schemas import ARAState, EntityRef, Provenance, Triple


@pytest.fixture
def kg_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("ARA_KG_BACKEND", "networkx")
    monkeypatch.setenv("ARA_KG_STORE", str(tmp_path / "kg.json"))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def _triple() -> dict[str, Any]:
    return Triple(
        subject=EntityRef(name="BRCA1", type="gene", id="brca1"),
        predicate="associated_with",
        object=EntityRef(name="Breast cancer", type="disease", id="breast_cancer"),
        confidence=0.9,
        provenance=Provenance(paper_id="PMID:1", chunk_id="0", span=0, extracted_by="test"),
    ).model_dump()


@pytest.mark.asyncio
async def test_interrupt_halts_before_graph_update_then_resume_writes(kg_env: Any) -> None:
    app = build_main_graph(MemorySaver())
    config = {"configurable": {"thread_id": "test-interrupt-1"}}
    state = ARAState(task="update kg with triples", valid_triples=[_triple()], errors=[])

    # 1) first invoke must HALT before graph_update
    await app.ainvoke(state, config)
    snap = app.get_state(config)
    assert snap.next == ("graph_update",), f"expected halt before graph_update, got {snap.next}"

    # 2) no writes happened while halted
    client = get_settings().client
    assert await client.subgraph(["brca1", "breast_cancer"], depth=1) == []

    # 3) resume with the same thread -> graph_update runs to completion
    await app.ainvoke(None, config=config)
    snap2 = app.get_state(config)
    assert snap2.next == (), f"expected graph ended, got {snap2.next}"
    edges = await client.subgraph(["brca1", "breast_cancer"], depth=1)
    assert len(edges) == 1
    assert edges[0].predicate == "associated_with"


@pytest.mark.asyncio
async def test_interrupt_does_not_trigger_on_other_routes(kg_env: Any) -> None:
    app = build_main_graph(MemorySaver())
    config = {"configurable": {"thread_id": "test-no-interrupt-1"}}
    state = ARAState(task="just checking status", errors=[])

    await app.ainvoke(state, config)
    snap = app.get_state(config)
    # routed to "end" — the run completed without halting at graph_update
    assert snap.next == (), f"expected immediate end, got {snap.next}"
