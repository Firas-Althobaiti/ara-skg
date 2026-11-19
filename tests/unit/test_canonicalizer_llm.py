"""Unit tests for the PredicateCanonicalizer LLM fallback + cache (issue #24)."""

from __future__ import annotations

import pytest

from ara.canonicalizer import PredicateCanonicalizer
from ara.config import get_settings


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _CountingLLM:
    model = "fake-model-v1"

    def __init__(self) -> None:
        self.calls = 0

    async def ainvoke(self, prompt: str) -> _FakeMessage:
        self.calls += 1
        return _FakeMessage("causes")


@pytest.mark.asyncio
async def test_llm_fallback_only_when_rule_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CANONICALIZER_MODE", "rule+llm")
    get_settings.cache_clear()
    llm = _CountingLLM()
    canon = PredicateCanonicalizer(llm=llm)

    assert await canon.canonicalize("causes") == "causes"  # rule knows it
    assert llm.calls == 0  # no LLM call for known predicates

    assert await canon.canonicalize("has_some_effect_on") == "causes"  # LLM fallback
    assert llm.calls == 1
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_cache_avoids_second_llm_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CANONICALIZER_MODE", "rule+llm")
    get_settings.cache_clear()
    llm = _CountingLLM()
    canon = PredicateCanonicalizer(llm=llm)

    first = await canon.llm_fallback("weird_verb_x")
    second = await canon.llm_fallback("weird_verb_x")
    assert first == second == "causes"
    assert llm.calls == 1  # second call served from cache

    # cache key includes the model: a different model must not reuse it
    other = _CountingLLM()
    other.model = "fake-model-v2"
    canon2 = PredicateCanonicalizer(llm=other)
    await canon2.llm_fallback("weird_verb_x")
    assert other.calls == 1
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_rule_mode_never_calls_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CANONICALIZER_MODE", "rule")
    get_settings.cache_clear()
    llm = _CountingLLM()
    canon = PredicateCanonicalizer(llm=llm)
    assert await canon.canonicalize("totally_unknown_verb") == "totally_unknown_verb"
    assert llm.calls == 0
    get_settings.cache_clear()


def test_rule_based_returns_none_for_unknown() -> None:
    canon = PredicateCanonicalizer()
    assert canon.rule_based("associated_with") == "associated_with"
    assert canon.rule_based("blocks") == "inhibits"
    assert canon.rule_based("completely_unknown") is None
