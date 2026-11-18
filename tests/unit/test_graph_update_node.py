"""Unit tests for the graph_update nodes' real rollback path (issue #10).

Mid-batch failure → state["errors"] populated, kg_delta cleared, and the
backend shows no partial writes after rollback_on_error.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ara.clients.kg_networkx import NetworkXKnowledgeGraphClient
from ara.config import get_settings
from ara.nodes.graph_update import rollback_on_error, upsert_kg_node
from ara.schemas import ARAState, EntityRef, Provenance, Triple


@pytest.fixture
def kg_env(tmp_path: Path, monkeypatch: Any) -> Any:
    monkeypatch.setenv("ARA_KG_BACKEND", "networkx")
    monkeypatch.setenv("ARA_KG_STORE", str(tmp_path / "kg.json"))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def _triple(s: str, o: str) -> Triple:
    return Triple(
        subject=EntityRef(name=s, type="gene", id=s.lower()),
        predicate="relates",
        object=EntityRef(name=o, type="protein", id=o.lower()),
        confidence=0.9,
        provenance=Provenance(paper_id="PMID:1", chunk_id="c1", span=0, extracted_by="test"),
    )


BATCH = [_triple("S0", "O0"), _triple("S1", "O1"), _triple("S2", "O2"), _triple("S3", "O3")]
ALL_IDS = ["s0", "s1", "s2", "s3", "o0", "o1", "o2", "o3"]


@pytest.mark.asyncio
async def test_mid_batch_failure_rolls_back_completely(kg_env: Any, monkeypatch: Any) -> None:
    client = get_settings().client
    assert isinstance(client, NetworkXKnowledgeGraphClient)
    original = client._apply_triple
    calls = {"n": 0}

    def failing(triple: Triple, now: str, delta: dict) -> None:
        calls["n"] += 1
        if calls["n"] == 3:
            raise RuntimeError("boom row 3")
        original(triple, now, delta)

    monkeypatch.setattr(client, "_apply_triple", failing)

    state = ARAState(
        task="update kg",
        resolved_triples=[t.model_dump() for t in BATCH],
        errors=[],
    )
    r1 = await upsert_kg_node(state)
    assert state["errors"], "failure must be recorded in errors"
    assert "boom row 3" in state["errors"][0]
    assert r1["kg_delta"] == []

    r2 = await rollback_on_error(state)
    assert r2["kg_delta"] == []
    assert state["kg_delta"] == []

    # backend shows NO partial writes (in-memory restored, nothing on disk)
    assert await client.subgraph(ALL_IDS, depth=1) == []
    assert not client.storage_path.exists()


@pytest.mark.asyncio
async def test_successful_upsert_persists_and_rollback_is_noop(kg_env: Any) -> None:
    client = get_settings().client
    state = ARAState(
        task="update kg",
        resolved_triples=[t.model_dump() for t in BATCH],
        errors=[],
    )
    r1 = await upsert_kg_node(state)
    assert state.get("errors") == []
    assert len(r1["kg_delta"]["edges"]) == 4
    assert client.storage_path.exists()  # saved once per batch, atomically

    await rollback_on_error(state)  # nothing failed → delta already set; cleared harmlessly
    assert state["kg_delta"] == []
    # successful writes are NOT undone by a later rollback call
    assert len(await client.subgraph(ALL_IDS, depth=1)) == 4
