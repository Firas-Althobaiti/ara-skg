"""Predicate canonicalizer with optional cached LLM fallback (issue #24).

Default mode is ``rule`` — pure synonym-table lookup, zero LLM cost. The
``rule+llm`` mode (``CANONICALIZER_MODE=rule+llm``) falls back to a cached
LLM call only when the rule table does not know the predicate. The cache key
includes the model name/version, so a model change never reuses stale
canonicalizations.
"""

from __future__ import annotations

from typing import Any

from ara.config import get_settings
from ara.logging import get_logger
from ara.schemas.predicates import (
    CANONICAL_PREDICATES,
    PREDICATE_SYNONYMS,
    canonicalize,
    is_canonical,
)

_FALLBACK_PROMPT = """Map the biomedical relation predicate below to the CLOSEST \
predicate from this canonical list:
{canonical}

Predicate to map: {predicate}

Reply with ONLY the canonical predicate string, nothing else."""


class PredicateCanonicalizer:
    """Canonicalize predicates: rule table first, optional cached LLM fallback."""

    def __init__(self, llm: Any = None) -> None:
        self._llm = llm
        # (model, predicate) → canonical predicate — in-memory per instance
        self._cache: dict[tuple[str, str], str] = {}

    def rule_based(self, predicate: str) -> str | None:
        """Return the canonical predicate if the rules know it, else None."""
        normalized = predicate.lower().strip().replace(" ", "_").replace("-", "_")
        if normalized in CANONICAL_PREDICATES:
            return normalized
        mapped = PREDICATE_SYNONYMS.get(normalized)
        return mapped  # None when unknown

    async def llm_fallback(self, predicate: str) -> str:
        """Ask the LLM for the closest canonical predicate (cached per model)."""
        from ara.llm import get_llm

        if self._llm is None:
            self._llm = get_llm("fast")
        model = str(getattr(self._llm, "model", "unknown"))
        key = (model, predicate)
        if key in self._cache:
            return self._cache[key]
        prompt = _FALLBACK_PROMPT.format(
            canonical=", ".join(CANONICAL_PREDICATES), predicate=predicate
        )
        response = await self._llm.ainvoke(prompt)
        text = str(getattr(response, "content", response)).strip().lower()
        text = text.replace(" ", "_").replace("-", "_").strip("`\"'.")
        result = text if is_canonical(text) else canonicalize(predicate)
        self._cache[key] = result
        get_logger("ara.canonicalizer").info(
            "llm fallback canonicalized predicate", predicate=predicate, result=result, model=model
        )
        return result

    async def canonicalize(self, predicate: str) -> str:
        """Canonicalize per ``CANONICALIZER_MODE``: rules, plus LLM fallback if enabled."""
        rule = self.rule_based(predicate)
        if rule is not None:
            return rule
        if get_settings().CANONICALIZER_MODE == "rule+llm":
            return await self.llm_fallback(predicate)
        return canonicalize(predicate)  # normalized pass-through


__all__ = ["PredicateCanonicalizer"]
