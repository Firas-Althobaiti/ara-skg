"""Unit tests for the rebuilt (non-circular) eval (issue #19)."""

from __future__ import annotations

import pytest

from ara.eval.extraction_f1 import (
    DISTRACTOR_PATH,
    GOLD_PATH,
    RAW_ABSTRACTS_DIR,
    REAL_GOLD_PATH,
    distractor_rejection_rate,
    eval_with_mode,
    load_gold,
    load_raw_abstracts,
)
from ara.schemas import Triple


def test_gold_files_exist_and_sized() -> None:
    assert len(load_gold(REAL_GOLD_PATH)) == 20
    assert len(load_gold(DISTRACTOR_PATH)) == 10
    raw = list(RAW_ABSTRACTS_DIR.glob("*.txt"))
    assert len(raw) >= 3
    assert sum(p.stat().st_size for p in raw) < 100 * 1024  # < 100KB total
    assert len(load_raw_abstracts()) == len(raw)


@pytest.mark.asyncio
async def test_eval_with_mode_mock_shape() -> None:
    res = await eval_with_mode("mock")
    assert res["mode"] == "mock"
    assert "f1" in res and "distractor_rejection" in res
    assert 0.0 <= res["distractor_rejection"] <= 1.0
    assert res["n_gold"] == 20


@pytest.mark.asyncio
async def test_distractor_rejection_never_exceeds_one() -> None:
    res = await eval_with_mode("mock")
    gold = load_gold(REAL_GOLD_PATH)
    # even a perfect (gold-echoing) predictor must score <= 1.0
    assert distractor_rejection_rate(gold, load_gold(DISTRACTOR_PATH)) <= 1.0
    assert res["distractor_rejection"] <= 1.0


@pytest.mark.asyncio
async def test_real_gold_measures_different_thing_than_circular_gold() -> None:
    """The mock's F1 on real abstracts must differ from the legacy circular
    measurement (mock parsing its own "S - p - O" format strings)."""
    from ara.eval.extraction_f1 import extract_predicted, extraction_f1

    real = await eval_with_mode("mock")  # real abstracts vs real-abstract gold
    legacy_pred = await extract_predicted()  # eval_papers() in mock format
    legacy_f1 = extraction_f1(legacy_pred, load_gold(GOLD_PATH))
    assert legacy_f1 == pytest.approx(0.9333, abs=0.01)  # circular: mock scores its own format
    assert real["f1"] != legacy_f1  # real gold measures something different


def _t(s: str, p: str, o: str) -> Triple:
    from ara.schemas import EntityRef, Provenance

    return Triple(
        subject=EntityRef(name=s, type="other", id=s),
        predicate=p,
        object=EntityRef(name=o, type="other", id=o),
        confidence=1.0,
        provenance=Provenance(paper_id="PMID:1", chunk_id="0", span=0, extracted_by="t"),
    )


def test_triple_match_predicate_exact_direction_preserved() -> None:
    from ara.eval.extraction_f1 import triple_match

    gold = _t("PARP inhibition", "causes", "apoptosis")
    assert triple_match(_t("inhibition of PARP", "causes", "apoptosis"), gold)  # fuzzy entity
    assert triple_match(_t("PARP inhibition", "trigger", "apoptosis"), gold)  # synonym → causes
    assert not triple_match(_t("PARP inhibition", "inhibits", "apoptosis"), gold)  # wrong predicate
    assert not triple_match(_t("apoptosis", "causes", "PARP inhibition"), gold)  # reversed


def test_distractor_rejection_still_guards_precision() -> None:
    from ara.eval.extraction_f1 import distractor_rejection_rate

    distractors = [
        _t("PARP inhibition", "inhibits", "apoptosis"),
        _t("apoptosis", "causes", "PARP inhibition"),
    ]
    good = [_t("inhibition of PARP", "causes", "apoptosis")]
    assert distractor_rejection_rate(good, distractors) == 1.0
    assert (
        distractor_rejection_rate(
            good + [_t("PARP inhibition", "inhibits", "apoptosis")], distractors
        )
        == 0.5
    )
