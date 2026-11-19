"""Evaluation metrics for ARA-SKG (Phase 12).

:func:`run_eval` runs the offline pipeline over the gold papers and returns
``{"extraction_f1": ..., "grounding": ...}``.  ``python -m ara.eval`` prints
the metrics as a rich table and exits non-zero when thresholds are missed.
"""

from __future__ import annotations

import asyncio

from ara.nodes.extraction import extract_relations_node, validate_triples_node
from ara.nodes.hypothesis import generate_hypotheses_node, ground_hypothesis_node
from ara.schemas import ARAState, coerce_triple

from .extraction_f1 import (
    DISTRACTOR_PATH,
    GOLD_PATH,
    REAL_GOLD_PATH,
    eval_papers,
    eval_with_mode,
    extract_predicted,
    extraction_f1,
    load_gold,
    prf1,
    triple_key,
)
from .grounding import grounding_score, is_grounded

__all__ = [
    "GOLD_PATH",
    "REAL_GOLD_PATH",
    "DISTRACTOR_PATH",
    "eval_papers",
    "eval_with_mode",
    "extract_predicted",
    "extraction_f1",
    "load_gold",
    "prf1",
    "triple_key",
    "grounding_score",
    "is_grounded",
    "run_eval",
]


def run_eval(mode: str = "mock") -> dict[str, float]:
    """Run the eval pipeline; return ``{"extraction_f1": ..., "grounding": ...}``.

    ``mode="mock"`` (default) is fully offline and CI-safe; ``mode="live"``
    uses the real LLM and requires ``OPENAI_API_KEY``.
    """

    async def _run() -> dict[str, float]:
        import os

        from ara.config import get_settings

        old = os.environ.get("EXTRACTION_MODE")
        os.environ["EXTRACTION_MODE"] = mode
        get_settings.cache_clear()
        try:
            state: ARAState = {"task": "phase-12 eval", "papers": eval_papers(), "errors": []}
            await extract_relations_node(state)
            await validate_triples_node(state)
            predicted = [coerce_triple(t) for t in state.get("valid_triples", [])]
            gold = load_gold()
            f1 = extraction_f1(predicted, gold)
            await generate_hypotheses_node(state)
            await ground_hypothesis_node(state)
            hypotheses = state.get("hypotheses", [])
            return {"extraction_f1": f1, "grounding": grounding_score(hypotheses)}
        finally:
            if old is None:
                os.environ.pop("EXTRACTION_MODE", None)
            else:
                os.environ["EXTRACTION_MODE"] = old
            get_settings.cache_clear()

    return asyncio.run(_run())
