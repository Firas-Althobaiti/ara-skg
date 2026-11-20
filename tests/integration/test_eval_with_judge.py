"""Integration tests: LLM-judge matching wired into prf1 (issue #28)."""

from __future__ import annotations

import pytest

from ara.eval.extraction_f1 import (
    distractor_rejection_rate,
    prf1,
    prf1_judged,
    triple_match,
)
from ara.eval.judge import BudgetExceededError, TripleJudge
from ara.prompts.judge import JudgeVerdict
from ara.schemas import EntityRef, Provenance, Triple


def _t(s: str, p: str, o: str) -> Triple:
    return Triple(
        subject=EntityRef(name=s, type="other", id=s),
        predicate=p,
        object=EntityRef(name=o, type="other", id=o),
        confidence=1.0,
        provenance=Provenance(paper_id="PMID:1", chunk_id="0", span=0, extracted_by="t"),
    )


class _FakeLLM:
    model = "stub-model"


def _judge_with(verdict: bool) -> TripleJudge:
    judge = TripleJudge(llm=_FakeLLM())

    async def _ask(prompt: str) -> JudgeVerdict:
        return JudgeVerdict(equivalent=verdict, confidence=0.9, reason="stub")

    judge._ask_llm = _ask  # type: ignore[method-assign]
    return judge


async def test_judge_match_improves_f1_over_exact_match() -> None:
    gold = [
        _t("PARP inhibition", "causes", "apoptosis"),
        # gold: "BRCA1 mutations predispose to breast cancer" (→ associated_with)
        _t("BRCA1 mutations", "associated_with", "breast cancer"),
    ]
    # pred 1 matches gold 1 by rules (synonym + fuzzy entity); pred 2 says
    # "causes" where gold says "associated_with" — only the judge can accept it.
    predicted = [
        _t("inhibition of PARP", "causes", "apoptosis"),
        _t("BRCA1 mutations", "causes", "breast cancer"),
    ]
    assert not triple_match(predicted[1], gold[1])

    rule = prf1(predicted, gold)
    judged = await prf1_judged(predicted, gold, _judge_with(True))
    # rule-only: 1 of 2 gold recalled, 1 of 2 predictions precise → F1 0.5
    assert rule["f1"] == pytest.approx(0.5)
    # judge accepts the causes/associated_with pair → perfect score
    assert judged["f1"] == pytest.approx(1.0)
    assert judged["f1"] > rule["f1"]


async def test_distractor_wrong_direction_still_rejected_with_judge() -> None:
    gold = [_t("PARP inhibitors", "activates", "RAD51 foci")]
    reversed_pred = _t("RAD51 foci", "activates", "PARP inhibitors")
    assert not triple_match(reversed_pred, gold[0])
    # even with a judge mocked to accept, direction reversal must not count —
    # the judge's entity check rejects it before any LLM call
    judge = _judge_with(True)
    judged = await prf1_judged([reversed_pred], gold, judge)
    assert judged["f1"] == 0.0
    assert judge.llm_calls == 0  # entities differ → no LLM call at all
    # and distractor_rejection is rule-only by construction
    assert distractor_rejection_rate([reversed_pred], [gold[0]]) == 1.0  # not emitted → rejected
    wrong_predicate = _t("PARP inhibitors", "inhibits", "RAD51 foci")
    assert (
        distractor_rejection_rate([wrong_predicate], [wrong_predicate]) == 0.0
    )  # emitted → caught


async def test_budget_guard_raises_during_prf1_judged() -> None:
    gold = [
        _t("PARP inhibitors", "involved_in", "gamma-H2AX foci"),
        _t("PARP inhibitors", "regulates", "gamma-H2AX foci"),
        _t("PARP inhibitors", "localized_to", "gamma-H2AX foci"),
    ]
    # matches none by rule (treats is positive_effect; gold predicates are own groups)
    predicted = [_t("PARP inhibitors", "treats", "gamma-H2AX foci")]
    judge = TripleJudge(llm=_FakeLLM(), max_calls=2)

    async def _ask(prompt: str) -> JudgeVerdict:
        return JudgeVerdict(equivalent=True, confidence=0.9, reason="stub")

    judge._ask_llm = _ask  # type: ignore[method-assign]
    with pytest.raises(BudgetExceededError, match="judge calls"):
        await prf1_judged(predicted, gold, judge)
