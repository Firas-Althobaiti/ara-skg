"""Hypothesis grounding metric.

A hypothesis counts as *grounded* when it has at least two supporting triples
and every supporting triple is provenance-linked (non-empty
``provenance.paper_id``).  :func:`grounding_score` is the fraction of grounded
hypotheses (``0.0`` when there are no hypotheses).
"""

from __future__ import annotations

from typing import Any

from ara.schemas import Hypothesis, coerce_triple


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Attribute-or-key access for Pydantic models and plain dicts alike."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def is_grounded(hypothesis: Hypothesis | dict[str, Any], min_support: int = 2) -> bool:
    """True when *hypothesis* has >= *min_support* provenance-linked triples."""
    supporting = _get(hypothesis, "supporting", []) or []
    if len(supporting) < min_support:
        return False
    for raw in supporting:
        t = coerce_triple(raw)
        if not t.provenance.paper_id:
            return False
    return True


def grounding_score(hypotheses: list[Hypothesis] | list[dict[str, Any]]) -> float:
    """Fraction of hypotheses with >= 2 provenance-linked supporting triples."""
    if not hypotheses:
        return 0.0
    grounded = sum(1 for h in hypotheses if is_grounded(h))
    return grounded / len(hypotheses)


__all__ = ["is_grounded", "grounding_score"]
