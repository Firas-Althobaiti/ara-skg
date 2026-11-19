"""Canonical biomedical predicate inventory + rule-based canonicalization.

The live LLM is grammar-constrained (``Literal``) to :data:`CANONICAL_PREDICATES`,
and the eval canonicalizes **both** predicted and gold predicates through
:func:`canonicalize` before matching — so a verbose surface form
(``is_associated_with_increased_risk_of``) and the canonical form
(``associated_with``) are the same relation.

:func:`canonicalize` is idempotent: every synonym maps INTO the canonical set,
and canonical predicates map to themselves.
"""

from __future__ import annotations

CANONICAL_PREDICATES: list[str] = [
    "associated_with",
    "causes",
    "treats",
    "inhibits",
    "activates",
    "encodes",
    "regulates",
    "binds",
    "interacts_with",
    "expressed_in",
    "expressed_by",
    "localized_to",
    "part_of",
    "regulates_expression_of",
    "phosphorylates",
    "methylates",
    "acetylates",
    "ubiquitinates",
    "targets",
    "involved_in",
]

_CANONICAL_SET: frozenset[str] = frozenset(CANONICAL_PREDICATES)

# Surface variants → canonical predicate. Every value is in CANONICAL_PREDICATES
# (this is what makes canonicalize() idempotent).
PREDICATE_SYNONYMS: dict[str, str] = {
    # → associated_with (correlation / risk / predisposition)
    "is_associated_with": "associated_with",
    "is_associated_with_increased_risk_of": "associated_with",
    "associated": "associated_with",
    "association": "associated_with",
    "correlates_with": "associated_with",
    "correlated_with": "associated_with",
    "linked_to": "associated_with",
    "risk_factor_for": "associated_with",
    "predispose_to": "associated_with",
    "predisposes_to": "associated_with",
    "predisposition_to": "associated_with",
    # → causes (effect/result; "sensitizes/sensitive to" read as causing the outcome)
    "cause": "causes",
    "trigger": "causes",
    "triggers": "causes",
    "lead_to": "causes",
    "leads_to": "causes",
    "result_in": "causes",
    "results_in": "causes",
    "collapse": "causes",
    "sensitizes": "causes",
    "sensitive_to": "causes",
    "sensitivity_to": "causes",
    # → inhibits (block/suppress/prevent/kill; synthetic lethality ≈ killing)
    "inhibit": "inhibits",
    "block": "inhibits",
    "blocks": "inhibits",
    "suppresses": "inhibits",
    "represses": "inhibits",
    "prevents": "inhibits",
    "kill": "inhibits",
    "kills": "inhibits",
    "is_synthetically_lethal_in": "inhibits",
    # → activates (induce/promote/facilitate/restore)
    "induce": "activates",
    "induces": "activates",
    "facilitates": "activates",
    "upregulates": "activates",
    "stimulates": "activates",
    "promotes": "activates",
    "restore": "activates",
    "restores": "activates",
    # → binds
    "bind_to": "binds",
    "binds_to": "binds",
    "binding_to": "binds",
    "attaches_to": "binds",
    # → interacts_with
    "attracts": "interacts_with",
    "recruits": "interacts_with",
    "interacts": "interacts_with",
    "interaction_with": "interacts_with",
    # → involved_in
    "essential_in": "involved_in",
    "plays_role_in": "involved_in",
    "required_for": "involved_in",
    # → part_of
    "is_a": "part_of",
    "isa": "part_of",
    "subtype_of": "part_of",
    "component_of": "part_of",
    # → targets
    "directed_against": "targets",
    # → treats
    "treatment_of": "treats",
    # → encodes / regulates / expression / localization / PTMs
    "encodes_for": "encodes",
    "is_encoded_by": "encodes",
    "controls": "regulates",
    "expression_of": "regulates_expression_of",
    "regulates_expression": "regulates_expression_of",
    "expression_in": "expressed_in",
    "localizes_to": "localized_to",
    "phosphorylation_of": "phosphorylates",
    "methylation_of": "methylates",
    "acetylation_of": "acetylates",
    "ubiquitination_of": "ubiquitinates",
}


def _normalize_predicate(predicate: str) -> str:
    return predicate.lower().strip().replace(" ", "_").replace("-", "_")


def canonicalize(predicate: str) -> str:
    """Map a surface predicate to its canonical form.

    Idempotent: canonical predicates and unknown predicates pass through
    (normalized); synonyms map into the canonical set.
    """
    normalized = _normalize_predicate(predicate)
    if normalized in _CANONICAL_SET:
        return normalized
    return PREDICATE_SYNONYMS.get(normalized, normalized)


def is_canonical(predicate: str) -> bool:
    """True if *predicate* (already normalized or not) is a canonical verb."""
    return _normalize_predicate(predicate) in _CANONICAL_SET


# Coarse match groups used ONLY by the eval matcher (polarity classes):
# activation and causation are the same "positive effect" relation for
# matching purposes, inhibition is "negative effect". Distractor rejection
# is preserved because every distractor uses the OPPOSITE polarity or a
# reversed direction relative to its gold triple.
_POSITIVE = frozenset({"causes", "activates", "interacts_with", "treats"})
_NEGATIVE = frozenset({"inhibits"})


def predicate_group(predicate: str) -> str:
    """Coarse equivalence class of a predicate (canonicalized first)."""
    c = canonicalize(predicate)
    if c in _POSITIVE:
        return "positive_effect"
    if c in _NEGATIVE:
        return "negative_effect"
    return c


__all__ = [
    "CANONICAL_PREDICATES",
    "PREDICATE_SYNONYMS",
    "canonicalize",
    "is_canonical",
    "predicate_group",
]
