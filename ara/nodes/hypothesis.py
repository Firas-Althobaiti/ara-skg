"""Hypothesis nodes: generate (strategy: mock default / live LLM) → ground → rank → critique."""

from __future__ import annotations

from typing import Any

from ara.config import get_settings
from ara.generators import get_generator
from ara.generators.mock import MockGenerator
from ara.logging import get_logger
from ara.schemas import ARAState, Hypothesis, coerce_triple


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


async def _call_llm(prompt: str, triples: list[Any] | None = None) -> list[Hypothesis]:
    """Backwards-compatible mock LLM call (tests monkeypatch this symbol).

    Delegates to :class:`ara.generators.mock.MockGenerator`; the real
    generate path goes through :func:`generate_hypotheses_node` and
    ``get_generator(get_settings().HYPOTHESIS_MODE)``.
    """
    parsed = [coerce_triple(t) for t in (triples or [])]
    return await MockGenerator().generate(parsed)


async def generate_hypotheses_node(state: ARAState) -> dict[str, Any]:
    """Generate hypotheses from the current KG context via the configured generator."""
    mode = get_settings().HYPOTHESIS_MODE
    if mode == "live":
        get_logger("ara.hypothesis").info(
            "live hypothesis mode — LLM calls incur cost", mode="live"
        )
    generator = get_generator(mode)
    context = state.get("valid_triples") or state.get("resolved_triples") or []
    hypotheses = await generator.generate([coerce_triple(t) for t in context])
    state["hypotheses"] = hypotheses
    return {"hypotheses": hypotheses}


async def ground_hypothesis_node(state: ARAState) -> dict[str, Any]:
    """Attach supporting triples to each hypothesis by entity overlap."""
    valid_triples = state.get("valid_triples") or state.get("resolved_triples") or []
    parsed = [coerce_triple(t) for t in valid_triples]
    hypotheses: list[Any] = state.get("hypotheses", [])
    for hyp in hypotheses:
        entities = set(_get(hyp, "entities", []) or [])
        supporting: list[Any] = []
        for raw, triple in zip(valid_triples, parsed, strict=False):
            names = {
                triple.subject.name,
                triple.subject.id or "",
                triple.object.name,
                triple.object.id or "",
            }
            if names & entities:
                supporting.append(raw)
        if isinstance(hyp, dict):
            hyp["supporting"] = supporting
        else:
            hyp.supporting = [coerce_triple(t) for t in supporting]
    state["hypotheses"] = hypotheses
    return {"hypotheses": hypotheses}


async def rank_hypotheses_node(state: ARAState) -> dict[str, Any]:
    """Rank hypotheses by combined novelty + plausibility (descending)."""
    hyps = state.get("hypotheses", [])
    hyps_sorted = sorted(
        hyps,
        key=lambda h: (_get(h, "novelty_score", 0.0) + _get(h, "plausibility_score", 0.0)),
        reverse=True,
    )
    state["hypotheses"] = hyps_sorted
    return {"hypotheses": hyps_sorted}


async def critique_hypothesis_node(state: ARAState) -> dict[str, Any]:
    """Reject hypotheses with fewer than two supporting triples."""
    hyps = state.get("hypotheses", [])
    valid_hyps = [h for h in hyps if len(_get(h, "supporting", []) or []) >= 2]
    if valid_hyps:
        critique = "All hypotheses are well supported."
    else:
        critique = "No valid hypotheses found (insufficient supporting evidence)."
    state["critique"] = critique
    state["hypotheses"] = valid_hyps
    return {"hypotheses": valid_hyps, "critique": critique}


__all__ = [
    "generate_hypotheses_node",
    "ground_hypothesis_node",
    "rank_hypotheses_node",
    "critique_hypothesis_node",
]
