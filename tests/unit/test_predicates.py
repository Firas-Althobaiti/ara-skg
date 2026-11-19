"""Unit tests for the canonical predicate inventory (issue #24)."""

from __future__ import annotations

from ara.schemas.predicates import CANONICAL_PREDICATES, canonicalize


def test_synonym_mappings() -> None:
    assert canonicalize("associated") == "associated_with"
    assert canonicalize("blocks") == "inhibits"
    assert canonicalize("upregulates") == "activates"
    assert canonicalize("is_associated_with_increased_risk_of") == "associated_with"
    assert canonicalize("binds_to") == "binds"
    assert canonicalize("induce") == "activates"


def test_unknown_passthrough() -> None:
    assert canonicalize("completely_unknown") == "completely_unknown"


def test_case_and_separator_normalization() -> None:
    assert canonicalize("INHIBITS") == "inhibits"
    assert canonicalize("Binds To") == "binds"
    assert canonicalize("associated-with") == "associated_with"


def test_all_canonical_predicates_are_fixed_points() -> None:
    assert len(CANONICAL_PREDICATES) == 20
    for p in CANONICAL_PREDICATES:
        assert canonicalize(p) == p


def test_canonicalize_is_idempotent() -> None:
    samples = [
        "associated",
        "blocks",
        "upregulates",
        "completely_unknown",
        "INHIBITS",
        "is_associated_with_increased_risk_of",
        "involved_in",
        "some brand new verb phrase",
    ]
    for s in samples:
        once = canonicalize(s)
        assert canonicalize(once) == once
