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
    GOLD_PATH,
    eval_papers,
    extract_predicted,
    extraction_f1,
    load_gold,
    prf1,
    triple_key,
)
from .grounding import grounding_score, is_grounded

__all__ = [
    "GOLD_PATH",
    "eval_papers",
    "extract_predicted",
    "extraction_f1",
    "load_gold",
    "prf1",
    "triple_key",
    "grounding_score",
    "is_grounded",
    "run_eval",
]


def run_eval() -> dict[str, float]:
    """Run the eval pipeline; return ``{"extraction_f1": ..., "grounding": ...}``.

    Fully offline: the deterministic mocked-LLM extractor and hypothesis
    generator are used, so no API key and no Neo4j are required.
    """

    async def _run() -> dict[str, float]:
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

    return asyncio.run(_run())
