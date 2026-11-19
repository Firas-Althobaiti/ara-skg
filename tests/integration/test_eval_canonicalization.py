"""Integration tests: canonicalization in eval matching (issue #24)."""

from __future__ import annotations

from ara.eval.extraction_f1 import distractor_rejection_rate, triple_match
from ara.schemas import EntityRef, Provenance, Triple


def _t(s: str, p: str, o: str) -> Triple:
    return Triple(
        subject=EntityRef(name=s, type="other", id=s),
        predicate=p,
        object=EntityRef(name=o, type="other", id=o),
        confidence=1.0,
        provenance=Provenance(paper_id="PMID:1", chunk_id="0", span=0, extracted_by="t"),
    )


def test_verbose_predicate_matches_canonical_gold() -> None:
    gold = _t("BRCA2 mutations", "associated_with", "breast cancer")
    pred = _t("BRCA2 mutations", "is_associated_with_increased_risk_of", "breast cancer")
    assert triple_match(pred, gold)


def test_synonym_predicate_matches_gold() -> None:
    gold = _t("PARP1", "binds", "DNA breaks")
    pred = _t("PARP1", "binds_to", "DNA breaks")
    assert triple_match(pred, gold)


def test_reversed_direction_distractor_still_rejected() -> None:
    gold = _t("PARP inhibitors", "causes", "RAD51 foci")
    reversed_distractor = _t("RAD51 foci", "causes", "PARP inhibitors")
    assert not triple_match(reversed_distractor, gold)
    assert distractor_rejection_rate([gold], [reversed_distractor]) == 1.0


def test_wrong_predicate_distractor_still_rejected() -> None:
    gold = _t("PARP1", "activates", "DNA repair")
    wrong_pred = _t("PARP1", "inhibits", "DNA repair")
    assert not triple_match(wrong_pred, gold)
    assert distractor_rejection_rate([gold], [wrong_pred]) == 1.0


def test_canonicalized_distractor_detected_when_emitted() -> None:
    # if the extractor emits the distractor's meaning under a canonical verb,
    # rejection must catch it (predicate canonicalizes to the same verb)
    distractor = _t("PARP inhibition", "prevents", "chromosomal instability")
    pred = _t("PARP inhibition", "inhibits", "chromosomal instability")  # prevents → inhibits
    assert triple_match(pred, distractor)
    assert distractor_rejection_rate([pred], [distractor]) == 0.0
