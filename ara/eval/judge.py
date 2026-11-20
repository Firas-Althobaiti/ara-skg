"""LLM-judge matching for semantic triple equivalence (issue #28).

:class:`TripleJudge` decides whether a predicted triple and a gold triple
express the same factual relation. The rule-based matcher
(:func:`ara.eval.extraction_f1.triple_match`) is always the fast path and is
the *only* matcher in mock mode; the LLM judge is consulted solely for
prediction/gold pairs the rules reject (live eval, ``JUDGE_MODE=rule+llm``).

Verdicts are cached twice: in-memory per judge instance, and on disk via
:mod:`ara.eval._llm_cache` when ``EVAL_CACHE=1``. The cache key includes the
prompt version, the model name, and hashes of the normalized predicted and
gold triples. Cache hits are free; only real LLM calls count against
``MAX_JUDGE_CALLS``, and exceeding the budget raises
:class:`BudgetExceededError` (never silently truncates).

The judge is NEVER used for distractor rejection — distractors are
near-misses by construction and must be rejected by the rules alone.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from ara.config import get_settings
from ara.logging import get_logger
from ara.prompts.judge import JUDGE_PROMPT, PROMPT_VERSION, JudgeVerdict
from ara.schemas import Triple, coerce_triple

from ._llm_cache import cache_enabled, cache_get, cache_set
from .extraction_f1 import entity_match, triple_key, triple_match


class BudgetExceededError(RuntimeError):
    """Raised when an eval run would exceed ``MAX_JUDGE_CALLS`` LLM-judge calls."""


def _hash_triple(t: Triple) -> str:
    return hashlib.sha256("|".join(triple_key(t)).encode()).hexdigest()[:16]


class TripleJudge:
    """Rule fast-path + cached LLM judge for triple equivalence."""

    def __init__(self, llm: Any = None, max_calls: int | None = None) -> None:
        self._llm = llm
        self._max_calls = max_calls if max_calls is not None else get_settings().MAX_JUDGE_CALLS
        # (model, pred_hash, gold_hash) → verdict — in-memory per instance
        self._mem: dict[tuple[str, str, str], bool] = {}
        # run statistics (see stats() / log_summary())
        self.rule_matched = 0
        self.llm_calls = 0
        self.llm_accepted = 0
        self.cache_hits = 0

    # -- LLM seam (monkeypatched in tests) -----------------------------------

    async def _ask_llm(self, prompt: str) -> JudgeVerdict:
        """Call the fast-tier LLM with structured output; returns the verdict."""
        from typing import cast

        from ara.llm import get_llm

        if self._llm is None:
            self._llm = get_llm("fast")
        runnable = self._llm.with_structured_output(JudgeVerdict)
        return cast(JudgeVerdict, await runnable.ainvoke(prompt))

    def _model(self) -> str:
        if self._llm is None:
            return "unknown"
        return str(getattr(self._llm, "model", "unknown"))

    # -- main entry point ------------------------------------------------------

    async def equivalent(self, predicted: Triple, gold: Triple) -> bool:
        """Return True iff *predicted* and *gold* express the same relation.

        Fast paths (no LLM call): the rule-based matcher accepts the pair, or
        the entities differ (the judge's own rules reject those, so spending
        an LLM call on them is pointless). Slow path: cached or live LLM
        judge with structured output.
        """
        p, g = coerce_triple(predicted), coerce_triple(gold)
        if triple_match(p, g):
            self.rule_matched += 1
            return True
        if not (
            entity_match(p.subject.name, g.subject.name)
            and entity_match(p.object.name, g.object.name)
        ):
            return False  # different entities → NOT equivalent (judge rule)

        model = self._model()
        key = (model, _hash_triple(p), _hash_triple(g))
        if key in self._mem:
            return self._mem[key]

        cache_key = f"judge|{PROMPT_VERSION}|{key[1]}|{key[2]}"
        if cache_enabled():
            cached = cache_get(cache_key, model)
            if cached is not None:
                self.cache_hits += 1
                verdict = json.loads(cached)["equivalent"]
                self._mem[key] = bool(verdict)
                return bool(verdict)

        if self.llm_calls >= self._max_calls:
            raise BudgetExceededError(
                f"eval-live exceeded {self._max_calls} LLM judge calls; "
                "reduce gold size or set JUDGE_MODE=rule"
            )
        self.llm_calls += 1
        prompt = JUDGE_PROMPT.format(
            p_subj=p.subject.name,
            p_pred=p.predicate,
            p_obj=p.object.name,
            g_subj=g.subject.name,
            g_pred=g.predicate,
            g_obj=g.object.name,
        )
        verdict = await self._ask_llm(prompt)
        result = bool(verdict.equivalent)
        if result:
            self.llm_accepted += 1
        self._mem[key] = result
        if cache_enabled():
            cache_set(cache_key, model, json.dumps(verdict.model_dump()))
        get_logger("ara.eval.judge").info(
            "judge verdict",
            equivalent=result,
            confidence=verdict.confidence,
            reason=verdict.reason,
            model=model,
        )
        return result

    # -- stats / logging --------------------------------------------------------

    def stats(self) -> dict[str, int]:
        """Run counters: total judged pairs and how each was resolved."""
        return {
            "total": self.rule_matched + self.llm_calls,
            "rule_matched": self.rule_matched,
            "llm_judged": self.llm_calls,
            "llm_accepted": self.llm_accepted,
            "cache_hits": self.cache_hits,
            "max_calls": self._max_calls,
        }

    def log_summary(self) -> None:
        s = self.stats()
        get_logger("ara.eval.judge").info(
            "judge calls: {total} (rule-matched: {rule_matched}, "
            "llm-judged: {llm_judged}, llm-accepted: {llm_accepted})".format(**s)
        )


__all__ = ["BudgetExceededError", "TripleJudge"]
