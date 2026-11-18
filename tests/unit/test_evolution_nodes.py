# File: tests/unit/test_evolution_nodes.py
import json

import pytest

from ara.nodes.evolution import (
    BASELINE_MARKER,
    detect_changes_node,
    load_prev_snapshot,
    save_snapshot,
    summarize_evolution_node,
)
from ara.schemas import ARAState


@pytest.mark.asyncio
async def test_detect_changes_fading_event():
    """Synthetic triples with a known drop → assert a `fading` event is detected."""
    prev = [
        {
            "subject": {"id": "geneA", "name": "GeneA", "type": "gene"},
            "predicate": "expresses",
            "object": {"id": "proteinX", "name": "ProteinX", "type": "protein"},
            "confidence": 0.9,
            "provenance": {
                "paper_id": "PMID:1",
                "chunk_id": "c1",
                "span": 0,
                "extracted_by": "tester",
            },
        }
    ]
    current = []  # geneA dropped
    state = ARAState(
        task="test",
        intent="evolve",
        papers=[],
        chunks=[],
        extracted_triples=[],
        valid_triples=current,
        prev_valid_triples=prev,
        errors=[],
        next_step=None,
        provenance={},
        budget=None,
        cypher="",
        params={},
        run_result={"result": [], "runtime": 0.0},
        final_answer="",
        **{},
    )
    result = await detect_changes_node(state)
    events = result.get("evolution_events", [])
    assert any(e["change_type"] == "fading" and e["entity_id"] == "geneA" for e in events)


def _triple(subj: str, pred: str, obj: str) -> dict:
    return {
        "subject": {"id": subj.lower(), "name": subj, "type": "gene"},
        "predicate": pred,
        "object": {"id": obj.lower(), "name": obj, "type": "protein"},
        "confidence": 0.9,
        "provenance": {
            "paper_id": "PMID:1",
            "chunk_id": "c1",
            "span": 0,
            "extracted_by": "tester",
        },
    }


@pytest.mark.asyncio
async def test_baseline_first_run_reports_zero_events() -> None:
    """First run on a populated KG (no previous snapshot): baseline mode.

    All existing triples must NOT be reported as "emerging"; the report must
    say a baseline was established.
    """
    current = [_triple("BRCA1", "regulates", "RAD51"), _triple("TP53", "regulates", "BRCA1")]
    state = ARAState(
        task="evolve all",
        valid_triples=current,
        prev_valid_triples=[],
        prev_baseline=True,
        errors=[],
    )
    detect_result = await detect_changes_node(state)
    assert detect_result["evolution_events"] == []

    report_result = await summarize_evolution_node(state)
    assert "baseline" in report_result["evolution_report"].lower()


@pytest.mark.asyncio
async def test_second_run_after_baseline_detects_exactly_new_triples() -> None:
    """Run 2 diffs current vs. the baseline snapshot: +2 triples → 2 events."""
    baseline = [_triple("BRCA1", "regulates", "RAD51")]
    current = baseline + [
        _triple("Olaparib", "inhibits", "PARP1"),
        _triple("PARP1", "involved_in", "DNA repair"),
    ]
    state = ARAState(
        task="evolve all",
        valid_triples=current,
        prev_valid_triples=baseline,
        prev_baseline=False,
        errors=[],
    )
    result = await detect_changes_node(state)
    events = result["evolution_events"]
    emerging = [e for e in events if e["change_type"] == "emerging"]
    assert len(emerging) == 2
    assert {e["entity_id"] for e in emerging} == {"olaparib", "parp1"}


def test_snapshot_roundtrip_baseline_marker(tmp_path) -> None:
    """load/save snapshot: missing file → baseline run; marker persisted."""
    prev_path = tmp_path / "kg.json.prev.json"

    triples, is_baseline = load_prev_snapshot(prev_path)
    assert is_baseline is True and triples == []

    save_snapshot(prev_path, triples=[_triple("BRCA1", "regulates", "RAD51")], baseline=True)
    raw = json.loads(prev_path.read_text(encoding="utf-8"))
    assert raw[BASELINE_MARKER] is True
    assert len(raw["triples"]) == 1

    # next run loads the baseline triples as a normal "previous" window
    triples2, is_baseline2 = load_prev_snapshot(prev_path)
    assert is_baseline2 is False
    assert len(triples2) == 1

    # non-baseline snapshot carries no marker
    save_snapshot(prev_path, triples=triples2, baseline=False)
    raw2 = json.loads(prev_path.read_text(encoding="utf-8"))
    assert BASELINE_MARKER not in raw2
