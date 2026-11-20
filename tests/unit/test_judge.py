"""Unit tests for the LLM-judge matcher (issue #28)."""

from __future__ import annotations

import pytest

from ara.eval.extraction_f1 import triple_match
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
    """Minimal stand-in for ChatOpenAI — only `.model` is read by the judge."""

    model = "stub-model"


def _stub_ask(judge: TripleJudge, verdicts: list[JudgeVerdict]) -> list[str]:
    """Replace ``_ask_llm`` with a stub popping verdicts; returns the prompts seen."""
    prompts: list[str] = []
    it = iter(verdicts)

    async def _ask(prompt: str) -> JudgeVerdict:
        prompts.append(prompt)
        return next(it)

    judge._ask_llm = _ask  # type: ignore[method-assign]
    return prompts


# causes (positive_effect) vs associated_with (own group) → rule rejects, judge decides
PRED = _t("BRCA1 mutations", "causes", "breast cancer")
GOLD = _t("BRCA1 mutations", "associated_with", "breast cancer")


async def test_rule_match_is_fast_path_and_skips_llm() -> None:
    """rule_based_match hit → True with ZERO LLM calls."""
    judge = TripleJudge(llm=_FakeLLM())

    async def _boom(prompt: str) -> JudgeVerdict:  # pragma: no cover - must not run
        raise AssertionError("LLM must not be called on a rule match")

    judge._ask_llm = _boom  # type: ignore[method-assign]
    p = _t("PARP1", "binds", "DNA breaks")
    g = _t("PARP1", "binds_to", "DNA breaks")  # synonym → same group
    assert triple_match(p, g)
    assert await judge.equivalent(p, g) is True
    assert judge.llm_calls == 0
    assert judge.rule_matched == 1


async def test_llm_verdict_equivalent_true() -> None:
    judge = TripleJudge(llm=_FakeLLM())
    _stub_ask(
        judge, [JudgeVerdict(equivalent=True, confidence=0.9, reason="risk implies association")]
    )
    assert not triple_match(PRED, GOLD)
    assert await judge.equivalent(PRED, GOLD) is True
    assert judge.llm_calls == 1
    assert judge.llm_accepted == 1


async def test_llm_verdict_equivalent_false() -> None:
    judge = TripleJudge(llm=_FakeLLM())
    _stub_ask(judge, [JudgeVerdict(equivalent=False, confidence=0.8, reason="different effect")])
    p = _t("PARP inhibitors", "inhibits", "gamma-H2AX foci")
    g = _t("PARP inhibitors", "activates", "gamma-H2AX foci")
    assert await judge.equivalent(p, g) is False
    assert judge.llm_calls == 1
    assert judge.llm_accepted == 0


async def test_second_call_for_same_pair_uses_cache_not_llm() -> None:
    judge = TripleJudge(llm=_FakeLLM())
    prompts = _stub_ask(
        judge,
        [
            JudgeVerdict(equivalent=True, confidence=0.9, reason="same"),
            JudgeVerdict(equivalent=True, confidence=0.9),
        ],
    )
    assert await judge.equivalent(PRED, GOLD) is True
    assert await judge.equivalent(PRED, GOLD) is True  # cached — no second LLM call
    assert judge.llm_calls == 1
    assert len(prompts) == 1


async def test_entity_mismatch_rejected_without_llm() -> None:
    """Paranoia: different entities → False on the LLM path too, and free."""
    judge = TripleJudge(llm=_FakeLLM())

    async def _boom(prompt: str) -> JudgeVerdict:  # pragma: no cover - must not run
        raise AssertionError("LLM must not be called when entities differ")

    judge._ask_llm = _boom  # type: ignore[method-assign]
    p = _t("BRCA1", "treats", "breast cancer")
    g = _t("BRCA2", "activates", "breast cancer")
    assert await judge.equivalent(p, g) is False
    assert judge.llm_calls == 0


async def test_budget_guard_raises_instead_of_truncating() -> None:
    judge = TripleJudge(llm=_FakeLLM(), max_calls=1)
    _stub_ask(
        judge,
        [
            JudgeVerdict(equivalent=True, confidence=0.9, reason="a"),
            JudgeVerdict(equivalent=True, confidence=0.9, reason="b"),
        ],
    )
    p = _t("BRCA1 mutations", "causes", "breast cancer")  # PRED
    g1 = _t("BRCA1 mutations", "associated_with", "breast cancer")  # GOLD
    g2 = _t("BRCA1 mutations", "regulates", "breast cancer")  # own group, entities match
    assert await judge.equivalent(p, g1) is True
    with pytest.raises(BudgetExceededError, match="judge calls"):
        await judge.equivalent(p, g2)
