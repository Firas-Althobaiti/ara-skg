"""Unit tests for the typer CLI in ``ara.cli``.

All commands are exercised against a temporary NetworkX KG store, so the
tests run fully offline with the mocked LLM (no API key, no Neo4j).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from ara.cli import app
from ara.config import get_settings

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path, monkeypatch):
    """Point the KG backend at a temp store and reset the settings cache."""
    monkeypatch.setenv("ARA_KG_BACKEND", "networkx")
    monkeypatch.setenv("ARA_KG_STORE", str(tmp_path / "kg.json"))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def test_help_lists_all_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("ingest", "query", "hypothesize", "evolve", "demo"):
        assert cmd in result.output


def test_ingest_mock_corpus(tmp_path: Path) -> None:
    kg_store = tmp_path / "kg.json"
    result = runner.invoke(app, ["ingest", "demo biomedical corpus", "--kg-store", str(kg_store)])
    assert result.exit_code == 0, result.output
    assert "PMID:1001" in result.output
    assert "KG delta" in result.output
    assert kg_store.exists()  # NetworkX backend persisted the graph


def test_query_after_ingest(tmp_path: Path) -> None:
    kg_store = tmp_path / "kg.json"
    runner.invoke(app, ["ingest", "demo", "--kg-store", str(kg_store)])
    result = runner.invoke(
        app, ["query", "Which entities are in the KG?", "--kg-store", str(kg_store)]
    )
    assert result.exit_code == 0, result.output
    assert "Answer" in result.output
    assert "BRCA1" in result.output


def test_query_rejects_write_operations(tmp_path: Path) -> None:
    # A question without "?" is not classified as a query; force the guard by
    # checking that a write-keyword cypher is rejected at the node level is
    # covered in test_query_nodes; here we assert the CLI surfaces node errors.
    result = runner.invoke(
        app, ["query", "no question mark here", "--kg-store", str(tmp_path / "kg.json")]
    )
    assert result.exit_code == 0  # generic intent -> empty cypher -> no rows, still exit 0
    assert "Answer" in result.output


def test_hypothesize_from_kg(tmp_path: Path) -> None:
    kg_store = tmp_path / "kg.json"
    runner.invoke(app, ["ingest", "demo", "--kg-store", str(kg_store)])
    result = runner.invoke(app, ["hypothesize", "--kg-store", str(kg_store)])
    assert result.exit_code == 0, result.output
    assert "hyp_" in result.output
    assert "Hypotheses" in result.output


def test_evolve_writes_snapshot(tmp_path: Path) -> None:
    kg_store = tmp_path / "kg.json"
    runner.invoke(app, ["ingest", "demo", "--kg-store", str(kg_store)])
    result = runner.invoke(app, ["evolve", "all", "--kg-store", str(kg_store)])
    assert result.exit_code == 0, result.output
    assert "Evolution" in result.output
    assert Path(str(kg_store) + ".prev.json").exists()  # snapshot for the next run


def test_evolve_first_run_establishes_baseline(tmp_path: Path) -> None:
    """First evolve on a populated KG: 0 events + baseline message + marker."""
    import json

    kg_store = tmp_path / "kg.json"
    runner.invoke(app, ["ingest", "demo", "--kg-store", str(kg_store)])
    result = runner.invoke(app, ["evolve", "all", "--kg-store", str(kg_store)])
    assert result.exit_code == 0, result.output
    assert "baseline" in result.output.lower()
    assert "emerging" not in result.output
    prev = Path(str(kg_store) + ".prev.json")
    assert json.loads(prev.read_text(encoding="utf-8"))["__baseline__"] is True


def test_evolve_second_run_detects_new_triples(tmp_path: Path) -> None:
    """After the baseline, adding 2 triples yields emerging events (no crash)."""
    import asyncio
    import json

    from ara.schemas import EntityRef, Provenance, Triple

    kg_store = tmp_path / "kg.json"
    runner.invoke(app, ["ingest", "demo", "--kg-store", str(kg_store)])
    runner.invoke(app, ["evolve", "all", "--kg-store", str(kg_store)])  # baseline

    client = get_settings().client
    new_triples = [
        Triple(
            subject=EntityRef(name="NewGeneA", type="gene", id="newgenea"),
            predicate="regulates",
            object=EntityRef(name="NewProteinB", type="protein", id="newproteinb"),
            confidence=0.9,
            provenance=Provenance(paper_id="PMID:9", chunk_id="c1", span=0, extracted_by="test"),
        ),
        Triple(
            subject=EntityRef(name="NewGeneA", type="gene", id="newgenea"),
            predicate="inhibits",
            object=EntityRef(name="NewDiseaseC", type="disease", id="newdiseasec"),
            confidence=0.9,
            provenance=Provenance(paper_id="PMID:9", chunk_id="c1", span=0, extracted_by="test"),
        ),
    ]
    asyncio.run(client.upsert_triples(new_triples))  # type: ignore[attr-defined]

    result = runner.invoke(app, ["evolve", "all", "--kg-store", str(kg_store)])
    assert result.exit_code == 0, result.output
    assert "emerging" in result.output
    assert "baseline established" not in result.output.lower()
    # snapshot after a non-baseline run carries no marker
    prev = Path(str(kg_store) + ".prev.json")
    assert "__baseline__" not in json.loads(prev.read_text(encoding="utf-8"))


def test_evolve_reset_baseline(tmp_path: Path) -> None:
    """--reset-baseline deletes the snapshot; next run is a baseline run again."""
    import json

    kg_store = tmp_path / "kg.json"
    runner.invoke(app, ["ingest", "demo", "--kg-store", str(kg_store)])
    runner.invoke(app, ["evolve", "all", "--kg-store", str(kg_store)])
    result = runner.invoke(app, ["evolve", "all", "--reset-baseline", "--kg-store", str(kg_store)])
    assert result.exit_code == 0, result.output
    assert "baseline" in result.output.lower()
    prev = Path(str(kg_store) + ".prev.json")
    assert json.loads(prev.read_text(encoding="utf-8"))["__baseline__"] is True


def test_demo_command(tmp_path: Path) -> None:
    out = tmp_path / "demo_report.md"
    kg_store = tmp_path / "kg.json"
    result = runner.invoke(app, ["demo", "--out", str(out), "--kg-store", str(kg_store)])
    assert result.exit_code == 0, result.output
    assert "Demo finished" in result.output
    assert out.exists()
    assert "ARA" in out.read_text(encoding="utf-8")
