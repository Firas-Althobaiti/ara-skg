"""Unit tests for the rule-based mismatch report used by ``eval --explain`` (#33)."""

from __future__ import annotations

from ara.eval.extraction_f1 import explain_mismatches
from ara.schemas import EntityRef, Provenance, Triple


def _t(s: str, p: str, o: str) -> Triple:
    return Triple(
        subject=EntityRef(name=s, type="other", id=s),
        predicate=p,
        object=EntityRef(name=o, type="other", id=o),
        confidence=1.0,
        provenance=Provenance(paper_id="PMID:1", chunk_id="0", span=0, extracted_by="t"),
    )


def test_explain_counts_unmatched_and_missed() -> None:
    gold = [
        _t("PARP inhibition", "causes", "apoptosis"),  # matched by pred 1
        _t("BRCA1 mutations", "associated_with", "breast cancer"),  # missed
        _t("RAD51", "involved_in", "DNA repair"),  # missed
    ]
    predicted = [
        _t("inhibition of PARP", "causes", "apoptosis"),  # rule-matches gold 1
        _t("PARP inhibitors", "treats", "gamma-H2AX foci"),  # matches no gold
    ]
    report = explain_mismatches(predicted, gold)
    assert len(report["missed_gold"]) == 2
    assert len(report["unmatched_predictions"]) == 1
    assert report["unmatched_predictions"][0]["triple"] == (
        "PARP inhibitors | treats | gamma-H2AX foci"
    )


def test_explain_best_candidate_is_highest_jaccard() -> None:
    gold = [_t("BRCA1 mutations", "associated_with", "breast cancer")]  # missed
    predicted = [
        _t("BRCA1 mutations", "causes", "breast cancer"),  # entity Jaccard 1.0 vs gold
        _t("BRCA2", "associated_with", "breast cancer"),  # lower Jaccard
        _t("PARP1", "involved_in", "DNA repair"),  # unrelated
    ]
    report = explain_mismatches(predicted, gold)
    assert len(report["missed_gold"]) == 1
    missed = report["missed_gold"][0]
    # "BRCA1 mutations causes breast cancer" shares ALL entity tokens with gold
    assert missed["best_candidate"] == "BRCA1 mutations | causes | breast cancer"
    assert missed["best_entity_jaccard"] == 1.0
    # the near-miss is reported even though the predicate differs (judge territory)
    assert "< 0.5" not in missed["reason"] or missed["best_entity_jaccard"] >= 0.5


def test_explain_no_predictions_reports_empty_candidate() -> None:
    report = explain_mismatches([], [_t("A", "causes", "B")])
    assert len(report["missed_gold"]) == 1
    assert report["missed_gold"][0]["best_candidate"] is None
    assert report["missed_gold"][0]["reason"] == "no predictions emitted"
