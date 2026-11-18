"""Hypothesis nodes: generate (mocked LLM) → ground → rank → critique."""

from __future__ import annotations

from typing import Any

from ara.schemas import ARAState, Hypothesis, coerce_triple


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


async def _call_llm(prompt: str, triples: list[Any] | None = None) -> list[Hypothesis]:
    """Mock LLM call returning exactly 3 :class:`Hypothesis` objects.

    When *triples* (the current KG context) are provided, the hypotheses are
    built from real extracted triples so that grounding can attach evidence;
    otherwise three static demo hypotheses are returned.  In production this
    would be::

        llm = get_llm('reason')
        generator = structured(llm, HypothesisGenerationResult)
        return (await generator.ainvoke(prompt)).hypotheses
    """
    parsed = [coerce_triple(t) for t in (triples or [])]
    if not parsed:
        return [
            Hypothesis(
                id="hyp_0",
                statement="GeneA directly activates ProteinX",
                mechanism="activation",
                entities=["geneA", "proteinX"],
                supporting=[],
                contradicting=[],
                novelty_score=0.65,
                plausibility_score=0.70,
                status="proposed",
            ),
            Hypothesis(
                id="hyp_1",
                statement="ProteinX inhibition reduces diseaseY progression",
                mechanism="inhibition",
                entities=["proteinX", "diseaseY"],
                supporting=[],
                contradicting=[],
                novelty_score=0.55,
                plausibility_score=0.65,
                status="proposed",
            ),
            Hypothesis(
                id="hyp_2",
                statement="GeneA expression correlates with diseaseY severity",
                mechanism="correlation",
                entities=["geneA", "diseaseY"],
                supporting=[],
                contradicting=[],
                novelty_score=0.45,
                plausibility_score=0.80,
                status="proposed",
            ),
        ]
    hypotheses: list[Hypothesis] = []
    for i, triple in enumerate(parsed[:3]):
        subj, obj = triple.subject, triple.object
        entities = [subj.name, subj.id or subj.name, obj.name, obj.id or obj.name]
        hypotheses.append(
            Hypothesis(
                id=f"hyp_{i}",
                statement=(
                    f"{subj.name} {triple.predicate} {obj.name} "
                    f"({triple.provenance.paper_id}) may drive disease-relevant mechanisms"
                ),
                mechanism=triple.predicate,
                entities=entities,
                supporting=[],
                contradicting=[],
                novelty_score=round(max(0.0, 0.95 - 0.15 * i), 2),
                plausibility_score=round(min(1.0, 0.6 + 0.1 * i), 2),
                status="proposed",
            )
        )
    while len(hypotheses) < 3:  # fewer than 3 triples: pad with generic ones
        i = len(hypotheses)
        hypotheses.append(
            Hypothesis(
                id=f"hyp_{i}",
                statement=f"Exploratory hypothesis {i} from limited evidence",
                mechanism="unknown",
                entities=[],
                supporting=[],
                contradicting=[],
                novelty_score=0.5,
                plausibility_score=0.5,
                status="proposed",
            )
        )
    return hypotheses[:3]


async def generate_hypotheses_node(state: ARAState) -> dict[str, Any]:
    """Generate 3 hypotheses from the current KG context (mocked LLM)."""
    context = state.get("valid_triples") or state.get("resolved_triples") or []
    hypotheses = await _call_llm("Generate 3 hypotheses based on the current context.", context)
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
