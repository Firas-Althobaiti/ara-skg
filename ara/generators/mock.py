"""Mock hypothesis generator: the deterministic logic moved verbatim from
``ara/nodes/hypothesis.py::_call_llm`` (no behavior change).
"""

from __future__ import annotations

from ara.schemas import Hypothesis, Triple

from .base import HypothesisGenerator


class MockGenerator:
    """Deterministic generator implementing :class:`HypothesisGenerator`."""

    async def generate(self, triples: list[Triple], n: int = 3) -> list[Hypothesis]:
        parsed = list(triples)
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
        for i, triple in enumerate(parsed[:n]):
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
        while len(hypotheses) < n:  # fewer than n triples: pad with generic ones
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
        return hypotheses[:n]


__all__ = ["MockGenerator", "HypothesisGenerator"]
