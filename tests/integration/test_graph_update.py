from ara.nodes.graph_update import (
    rollback_on_error,
    upsert_kg_node,
)
from ara.schemas.triple import Provenance, Triple


# Simple in-memory mock client for testing
class MockKGClient:
    def __init__(self):
        self.added_keys = set()  # (subject_id, predicate, object_id)

    async def upsert_triples(self, triples):
        added = 0
        for triple in triples:
            key = (triple.subject.id, triple.predicate, triple.object.id)
            if key not in self.added_keys:
                self.added_keys.add(key)
                added += 1
        return {"added": added, "updated": 0}

    async def rollback(self):
        # no-op for this test
        pass


async def test_upsert_idempotent(monkeypatch):
    mock_client = MockKGClient()

    # inject client via settings
    class DummySettings:
        client = mock_client

    monkeypatch.setattr("ara.nodes.graph_update.get_settings", lambda: DummySettings())

    # Build state with two identical triples (duplicate keys)
    triple = Triple(
        subject={"name": "geneA", "type": "gene", "id": "geneA"},
        predicate="expresses",
        object={"name": "proteinX", "type": "protein", "id": "proteinX"},
        confidence=0.9,
        provenance=Provenance(
            paper_id="PMID:001",
            chunk_id="c1",
            span=0,
            extracted_by="tester",
        ),
    )
    state = {
        "task": "test",
        "papers": [],
        "chunks": [],
        "extracted_triples": [triple, triple],  # duplicate list
        "valid_triples": [triple, triple],
        "kg_delta": [],
        "errors": [],
        "next_step": None,
        "provenance": {},
        "budget": None,
        "cypher": "",
        "params": {},
        "run_result": {"result": [], "runtime": 0.0},
        "final_answer": "",
        **{},
    }

    # First upsert
    await upsert_kg_node(state)
    # Second call with same list should add 0 new keys (idempotent)
    await upsert_kg_node(state)

    # Verify that the mock client saw only one unique key
    assert len(mock_client.added_keys) == 1


async def test_mid_batch_failure(monkeypatch):
    # mock client that raises on second upsert call
    class FailingKGClient:
        def __init__(self):
            self.added_keys = set()

        async def upsert_triples(self, triples):
            if len(triples) > 1:
                raise RuntimeError("simulated failure")
            for triple in triples:
                self.added_keys.add((triple.subject.id, triples[0].predicate, triples[0].object.id))
            return {"added": len(triples), "updated": 0}

        async def rollback(self):
            pass

    class DummySettings:
        client = FailingKGClient()

    monkeypatch.setattr("ara.nodes.graph_update.get_settings", lambda: DummySettings())

    # Build state with two triples (will cause failure on second upsert)
    triple1 = Triple(
        subject={"name": "geneA", "type": "gene", "id": "geneA"},
        predicate="expresses",
        object={"name": "proteinX", "type": "protein", "id": "proteinX"},
        confidence=0.9,
        provenance=Provenance(
            paper_id="PMID:001",
            chunk_id="c1",
            span=0,
            extracted_by="tester",
        ),
    )
    triple2 = Triple(
        subject={"name": "geneB", "type": "gene", "id": "geneB"},
        predicate="binds",
        object={"name": "proteinY", "type": "protein", "id": "proteinY"},
        confidence=0.8,
        provenance=Provenance(
            paper_id="PMID:001",
            chunk_id="c1",
            span=0,
            extracted_by="tester",
        ),
    )
    state = {
        "task": "test",
        "papers": [],
        "chunks": [],
        "extracted_triples": [triple1, triple2],
        "valid_triples": [triple1, triple2],
        "kg_delta": [],
        "errors": [],
        "next_step": None,
        "provenance": {},
        "budget": None,
        "cypher": "",
        "params": {},
        "run_result": {"result": [], "runtime": 0.0},
        "final_answer": "",
        **{},
    }

    await upsert_kg_node(state)  # first call succeeds
    await rollback_on_error(state)  # handle error (rolls back delta)
    # After rollback delta should be cleared
    assert state["kg_delta"] == []
