"""Live LLM hypothesis generator (requires ``OPENAI_API_KEY``).

Prompt + schema in :mod:`ara.prompts.hypothesis_live`. Supports the
``EVAL_CACHE=1`` file cache to keep repeated live runs under the cost cap.
"""

from __future__ import annotations

import json
from typing import Any, TypeVar

from pydantic import BaseModel

from ara.llm import get_llm
from ara.prompts.hypothesis_live import HYPOTHESIS_PROMPT, HypothesisGeneration
from ara.schemas import Hypothesis, Triple

from .base import HypothesisGenerator

T = TypeVar("T", bound=BaseModel)


def _render_context(triples: list[Triple]) -> str:
    if not triples:
        return "(empty knowledge graph)"
    return "\n".join(
        f"- {t.subject.name} -[{t.predicate}]-> {t.object.name} "
        f"(conf={t.confidence:.2f}, source={t.provenance.paper_id})"
        for t in triples
    )


class LLMGenerator:
    """LLM-backed :class:`HypothesisGenerator`."""

    def __init__(self, tier: Any = "reason") -> None:
        self._tier = tier
        self._llm: Any = None

    def _get_llm(self) -> Any:
        if self._llm is None:
            self._llm = get_llm(self._tier)
        return self._llm

    async def generate(self, triples: list[Triple], n: int = 3) -> list[Hypothesis]:
        from ara.eval._llm_cache import cache_enabled, cache_get, cache_set

        llm = self._get_llm()
        model = str(getattr(llm, "model", "unknown"))
        prompt = HYPOTHESIS_PROMPT.format(context=_render_context(triples), n=n)
        if cache_enabled():
            hit = cache_get(prompt, model)
            if hit is not None:
                result = HypothesisGeneration.model_validate(json.loads(hit))
            else:
                result = await llm.with_structured_output(HypothesisGeneration).ainvoke(prompt)
                cache_set(prompt, model, result.model_dump_json())
        else:
            result = await llm.with_structured_output(HypothesisGeneration).ainvoke(prompt)
        return [
            Hypothesis(
                id=f"hyp_{i}",
                statement=h.statement,
                mechanism=h.mechanism,
                entities=h.entities,
                supporting=[],
                contradicting=[],
                novelty_score=h.novelty_score,
                plausibility_score=h.plausibility_score,
                status="proposed",
            )
            for i, h in enumerate(result.hypotheses[:n])
        ]


__all__ = ["LLMGenerator", "HypothesisGenerator"]
