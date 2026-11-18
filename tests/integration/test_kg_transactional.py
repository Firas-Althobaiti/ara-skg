"""Integration tests: transactional KG writes on BOTH backends (issue #10).

A mid-batch failure (3rd triple of 4 raises) must leave ZERO persisted
triples, raise KGWriteError, and a clean retry must succeed fully.

The Neo4j backend is exercised through a fake driver/session that faithfully
implements transaction semantics: ``execute_write`` commits the mutated
store only if the work function returns; on exception it restores a
deep-copied snapshot (rollback). This proves the client sends the whole
batch in ONE ``execute_write`` call and surfaces failures as KGWriteError.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

from ara.clients.kg import KGWriteError
from ara.clients.kg_networkx import NetworkXKnowledgeGraphClient
from ara.clients.neo4j import Neo4jKnowledgeGraphClient
from ara.schemas import EntityRef, Provenance, Triple


def _triple(s: str, p: str, o: str) -> Triple:
    return Triple(
        subject=EntityRef(name=s, type="gene", id=s.lower()),
        predicate=p,
        object=EntityRef(name=o, type="protein", id=o.lower()),
        confidence=0.9,
        provenance=Provenance(paper_id="PMID:1", chunk_id="c1", span=0, extracted_by="test"),
    )


BATCH = [
    _triple("S1", "relates", "O1"),
    _triple("S2", "relates", "O2"),
    _triple("S3", "relates", "O3"),
    _triple("S4", "relates", "O4"),
]
ALL_IDS = ["s1", "s2", "s3", "s4", "o1", "o2", "o3", "o4"]


# ---------------------------------------------------------------------------
# Minimal fake Neo4j driver with real transaction semantics
# ---------------------------------------------------------------------------
class _FakeCursor:
    def __init__(self, records: list[dict[str, Any]]) -> None:
        self._records = records

    def __aiter__(self) -> Any:
        async def gen() -> Any:
            for r in self._records:
                yield r

        return gen()


class _FakeTx:
    def __init__(self, store: dict[str, Any], fail_on_row: int | None) -> None:
        self.store = store
        self.fail_on_row = fail_on_row
        self.i = 0

    async def run(self, query: str, **kwargs: Any) -> _FakeCursor:
        rows = kwargs.get("rows") or []
        records: list[dict[str, Any]] = []
        if "UNWIND" in query:  # the batch upsert query
            for row in rows:
                self.i += 1
                if self.fail_on_row is not None and self.i == self.fail_on_row:
                    raise RuntimeError(f"injected failure on row {self.i}")
                key = (row["subject_id"], row["predicate"], row["object_id"])
                was_present = key in self.store["edges"]
                self.store["edges"][key] = {
                    "confidence": row["conf"],
                    "provenance": row["prov"],
                }
                self.store["nodes"][row["subject_id"]] = {"name": row["subject_name"]}
                self.store["nodes"][row["object_id"]] = {"name": row["object_name"]}
                records.append(
                    {
                        "subject": row["subject_id"],
                        "predicate": row["predicate"],
                        "object": row["object_id"],
                        "was_present": was_present,
                    }
                )
            return _FakeCursor(records)
        # subgraph / temporal queries: MATCH (s:Entity)-[r:REL]->(o:Entity) ...
        ids = set(kwargs.get("ids", []))
        for (s, p, o), props in self.store["edges"].items():
            if s in ids or o in ids:
                records.append(
                    {
                        "s": {
                            "id": s,
                            "name": self.store["nodes"].get(s, {}).get("name", s),
                            "type": "gene",
                        },
                        "r": {
                            "predicate": p,
                            "confidence": props["confidence"],
                            "provenance": props["provenance"],
                        },
                        "o": {
                            "id": o,
                            "name": self.store["nodes"].get(o, {}).get("name", o),
                            "type": "protein",
                        },
                    }
                )
        return _FakeCursor(records)


class _FakeSession:
    def __init__(self, store: dict[str, Any], fail_on_row: int | None) -> None:
        self.store = store
        self.fail_on_row = fail_on_row

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def execute_write(self, work: Any) -> Any:
        snapshot = copy.deepcopy(self.store)
        tx = _FakeTx(self.store, self.fail_on_row)
        try:
            return await work(tx)  # success → commit (keep mutated store)
        except Exception:
            self.store.clear()
            self.store.update(snapshot)  # failure → rollback
            raise

    async def run(self, query: str, **kwargs: Any) -> _FakeCursor:
        return await _FakeTx(self.store, None).run(query, **kwargs)


class _FakeDriver:
    def __init__(self, store: dict[str, Any], fail_on_row: int | None) -> None:
        self.store = store
        self.fail_on_row = fail_on_row

    def session(self) -> _FakeSession:
        return _FakeSession(self.store, self.fail_on_row)

    async def close(self) -> None:
        return None


# ---------------------------------------------------------------------------
# Parametrized backend factory
# ---------------------------------------------------------------------------
@pytest.fixture(params=["networkx", "neo4j"])
def backend_factory(request: Any, tmp_path: Any, monkeypatch: Any) -> Any:
    def make(fail_on_3rd: bool) -> Any:
        if request.param == "networkx":
            client = NetworkXKnowledgeGraphClient(
                storage_path=str(tmp_path / f"kg_{fail_on_3rd}.json")
            )
            if fail_on_3rd:
                original = client._apply_triple
                calls = {"n": 0}

                def failing(triple: Triple, now: str, delta: dict) -> None:
                    calls["n"] += 1
                    if calls["n"] == 3:
                        raise RuntimeError("injected mid-batch failure (row 3)")
                    original(triple, now, delta)

                monkeypatch.setattr(client, "_apply_triple", failing)
            return client
        store: dict[str, Any] = {"nodes": {}, "edges": {}}
        client = Neo4jKnowledgeGraphClient("bolt://fake", "u", "p")
        client.driver = _FakeDriver(store, fail_on_row=3 if fail_on_3rd else None)
        return client

    return request.param, make


@pytest.mark.asyncio
async def test_partial_failure_persists_nothing_then_clean_retry_succeeds(
    backend_factory: Any,
) -> None:
    name, make = backend_factory

    # 1) failing client: 3rd triple of 4 raises mid-batch
    failing_client = make(fail_on_3rd=True)
    with pytest.raises(KGWriteError) as excinfo:
        await failing_client.upsert_triples(BATCH)
    assert "rolled back" in str(excinfo.value) or "restored" in str(excinfo.value)

    # 2) nothing persisted — subgraph over all touched entities is EMPTY
    assert await failing_client.subgraph(ALL_IDS, depth=1) == []
    if name == "networkx":
        assert not failing_client.storage_path.exists()  # no partial file written
    else:
        assert failing_client.driver.store["edges"] == {}

    # 3) idempotent retry with a clean batch succeeds fully
    clean = make(fail_on_3rd=False)
    delta = await clean.upsert_triples(BATCH)
    assert len(delta["edges"]) == 4
    assert len(await clean.subgraph(ALL_IDS, depth=1)) == 4

    delta2 = await clean.upsert_triples(BATCH)  # re-run: still 4 edges, no dupes
    assert len(delta2["edges"]) == 4
    assert len(await clean.subgraph(ALL_IDS, depth=1)) == 4
