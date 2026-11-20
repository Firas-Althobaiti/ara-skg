"""LLM-judge prompt + structured-output schema for triple equivalence (issue #28).

The judge decides whether a PREDICTED triple and a GOLD triple (both from the
same paper abstract) express the same factual relation. It is only consulted
for pairs the rule-based matcher (:func:`ara.eval.extraction_f1.triple_match`)
rejects — the rules stay the fast path, and distractor rejection never uses
the judge.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# Bump when the prompt text changes — the judge cache key includes it, so a
# prompt revision never reuses stale verdicts.
PROMPT_VERSION = "v1"

JUDGE_PROMPT = """You are a biomedical fact-checker. Given a PREDICTED triple and a \
GOLD triple (both from the same paper abstract), decide if they express the \
same factual relation.

PREDICTED: subject="{p_subj}", predicate="{p_pred}", object="{p_obj}"
GOLD:      subject="{g_subj}", predicate="{g_pred}", object="{g_obj}"

Rules:
- Different entities (subject or object) → NOT equivalent.
- Opposite direction (A inhibits B vs B inhibits A) → NOT equivalent.
- Semantically identical predicates (treats/induces for drug effects; \
predispose_to/associated_with when the text implies risk) → equivalent.
- One entity is a subset/superset of the other's → NOT equivalent.
- Negation mismatch → NOT equivalent.

Output JSON: {{"equivalent": bool, "confidence": 0.0-1.0, "reason": "<one sentence>"}}"""


class JudgeVerdict(BaseModel):
    """Structured output of the LLM judge."""

    equivalent: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = ""


__all__ = ["JUDGE_PROMPT", "PROMPT_VERSION", "JudgeVerdict"]
