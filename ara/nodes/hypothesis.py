from typing import Dict, Any, List
from ara.state import ARAState
from ara.schemas import Hypothesis, HypothesisGenerationResult
from ara.config import get_settings
from tenacity import retry, stop_after_attempt, wait_exponential
import asyncio

# ----------------------------------------------------------------------
# Helper: dummy LLM call (mocked). In a real system this would call the LLM.
# ----------------------------------------------------------------------
class DummyMessage:
    def __init__(self, content: str):
        self.content = content

async def _call_llm(prompt: str) -> List[Hypothesis]:
    """
    Mock LLM call that returns a list of 3 dummy Hypothesis objects.
    In production this would be:
        llm = get_llm('reason')
        schema = HypothesisGenerationResult
        generator = structured(llm, schema)
        msg = DummyMessage(prompt)
        result = await generator.run(msg)   # type: ignore
        return result.hypotheses
    """
    # mock data
    hyp1 = Hypothesis(
        id="hyp_0",
        statement="GeneA directly activates ProteinX",
        mechanism="activation",
        entities=[],
        supporting=[],
        contradicting=[],
        novelty_score=0.65,
        plausibility_score=0.70,
        status="proposed",
    )
    hyp2 = Hypothesis(
        id="hyp_1",
        statement="ProteinX inhibition reduces diseaseY progression",
        mechanism="inhibition",
        entities=[],
        supporting=[],
        contradicting=[],
        novelty_score=0.55,
        plausibility_score=0.65,
        status="proposed",
    )
    hyp3 = Hypothesis(
        id="hyp_2",
        statement="GeneA expression correlates with diseaseY severity",
        mechanism="correlation",
        entities=[],
        supporting=[],
        contradicting=[],
        novelty_score=0.45,
        plausibility_score=0.80,
        status="proposed",
    )
    return [hyp1, hyp2, hyp3]

async def generate_hypotheses_node(state: ARAState) -> Dict[str, Any]:
    """Generate a list of hypotheses based on the current context."""
    # In a real implementation we would pass the current context (e.g., valid triples)
    # to the LLM. Here we simply call the dummy LLM.
    hypotheses = await _call_llm("Generate 3 hypotheses based on the current context.")
    state["hypotheses"] = hypotheses
    return state

async def ground_hypothesis_node(state: ARAState) -> Dict[str, Any]:
    """Attach supporting triples to each hypothesis based on entity overlap."""
    valid_triples: List[dict] = state.get("valid_triples", [])
    hypotheses: List[Hypothesis] = state.get("hypotheses", [])

    for hyp in hypotheses:
        # naive matching: if the hypothesis mentions any entity that appears in a triple,
        # we consider that triple supporting.
        supporting = []
        for triple in valid_triples:
            # naive check: if subject or object name appears in the hypothesis entities list
            # (hypothesis entities are stored as a list of names)
            if hasattr(hyp, "entities") and isinstance(hyp.entities, list):
                for triple in valid_triples:
                    subj_name = triple["subject"]["name"]
                    obj_name = triple["object"]["name"]
                    if subj_name in hyp.entities or obj_name in hyp.entities:
                        supporting.append(triple)
        hyp["supporting"] = supporting  # attach supporting triples (as dicts)

    return state

async def rank_hypotheses_node(state: ARAState) -> Dict[str, Any]:
    """Rank hypotheses by combined novelty + plausibility score (descending)."""
    hyps: List[Hypothesis] = state.get("hypotheses", [])
    # sort by combined score
    hyps_sorted = sorted(
        hyps,
        key=lambda h: (h.novelty_score + h.plausibility_score),
        reverse=True,
    )
    state["hypotheses"] = hyps_sorted
    return state

async def critique_hypothesis_node(state: ARAState) -> Dict[str, Any]:
    """Reject hypotheses that have fewer than two supporting triples."""
    hyps: List[Hypothesis] = state.get("hypotheses", [])
    valid_hyps = []
    for hyp in hyps:
        supporting = getattr(hyp, "supporting", [])
        if len(valid_triples := supporting) >= 2:
            valid_hyps.append(hyp)
    if valid_hyps:
        state["critique"] = "All hypotheses are well supported."
    else:
        state["critique"] = "No valid hypotheses found (insufficient supporting evidence)."
    state["hypotheses"] = valid_hyps
    return state
