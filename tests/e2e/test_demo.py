"""End-to-end tests for ``scripts/demo.py`` and ``scripts/seed_neo4j.py``.

The demo runs against the offline NetworkX backend with the mocked LLM; the
seed script's builder and its idempotent ``seed()`` are tested against a
temporary :class:`NetworkXKnowledgeGraphClient` (no live Neo4j needed — the
``MERGE``/upsert semantics are the same code path the Neo4j client uses).
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

from ara.clients.kg_networkx import NetworkXKnowledgeGraphClient

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_script(file_name: str, module_name: str):
    """Import a script from ``scripts/`` as a module (scripts is not a package)."""
    path = REPO_ROOT / "scripts" / file_name
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def demo_module():
    return _load_script("demo.py", "ara_demo_script")


@pytest.fixture(scope="module")
def seed_module():
    return _load_script("seed_neo4j.py", "ara_seed_script")


@pytest.fixture(autouse=True)
def _clean_settings_cache(monkeypatch):
    from ara.config import get_settings

    # run_demo()/cli mutate os.environ directly — snapshot and restore them
    monkeypatch.setenv("ARA_KG_BACKEND", os.environ.get("ARA_KG_BACKEND", "networkx"))
    monkeypatch.setenv("ARA_KG_STORE", os.environ.get("ARA_KG_STORE", "kg_store.json"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_demo_runs_end_to_end(demo_module, tmp_path, monkeypatch):
    monkeypatch.setenv("ARA_KG_BACKEND", "networkx")
    out = tmp_path / "demo_report.md"
    kg_store = tmp_path / "demo_kg.json"

    final = await demo_module.run_demo(out_path=out, kg_store=str(kg_store))

    assert final["errors"] == []
    # 3 mock papers ingested
    papers = final["papers"]
    assert len(papers) == 3
    assert {p.id if not isinstance(p, dict) else p["id"] for p in papers} == {
        "PMID:1001",
        "PMID:1002",
        "PMID:1003",
    }
    # 3 papers x 3 relations = 9 triples extracted, validated and upserted
    assert len(final["valid_triples"]) == 9
    delta = final["kg_delta"]
    assert delta["added"] > 0
    # 3 hypotheses, all grounded with >= 2 supporting triples (critique keeps them)
    hypotheses = final["hypotheses"]
    assert len(hypotheses) == 3
    assert all(
        len(h.supporting if not isinstance(h, dict) else h["supporting"]) >= 2 for h in hypotheses
    )
    # 1 experiment proposed from the top hypothesis
    exp = final["experiment"]
    top_id = hypotheses[0].id if not isinstance(hypotheses[0], dict) else hypotheses[0]["id"]
    assert (exp.get("hypothesis_id") if isinstance(exp, dict) else exp.hypothesis_id) == top_id
    # evolution report produced
    assert isinstance(final["evolution_report"], str) and final["evolution_report"]
    assert len(final["evolution_events"]) > 0
    # artifacts written
    assert out.exists()
    report = out.read_text(encoding="utf-8")
    assert report.startswith("# ARA") or "# ARA" in report
    assert "## 6) Evolution report" in report
    assert kg_store.exists()


def test_demo_graph_wiring(demo_module):
    app = demo_module.build_demo_graph()
    node_ids = set(app.get_graph().nodes.keys())
    expected = {
        "ingest",
        "extract_entities",
        "extract_relations",
        "link_entities",
        "validate_triples",
        "resolve_triples",
        "ensure_schema",
        "upsert_kg",
        "generate_hypotheses",
        "ground_hypotheses",
        "rank_hypotheses",
        "critique_hypotheses",
        "propose_experiment",
        "validate_experiment",
        "evolution_window",
        "evolution_detect",
        "evolution_summarize",
    }
    assert expected <= node_ids


def test_seed_builds_30_triples(seed_module):
    triples = seed_module.build_seed_triples()
    assert len(triples) == 30
    keys = {(t.subject.id, t.predicate, t.object.id) for t in triples}
    assert len(keys) == 30  # all unique
    assert all(0.0 <= t.confidence <= 1.0 for t in triples)
    assert all(t.provenance.paper_id.startswith("PMID:") for t in triples)


@pytest.mark.asyncio
async def test_seed_is_idempotent(seed_module, tmp_path):
    """seed() twice against a KG client: second run adds nothing (MERGE semantics)."""
    client = NetworkXKnowledgeGraphClient(storage_path=str(tmp_path / "seed_kg.json"))
    first = await seed_module.seed(client)
    second = await seed_module.seed(client)
    assert first["added"] > 0
    assert second["added"] == 0
    assert second["updated"] == 30
    assert client.stats()["edges"] == 30
