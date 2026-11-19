"""Unit tests for the hypothesis generators (issue #19)."""

from __future__ import annotations

import pytest

from ara.generators import LLMGenerator, MockGenerator, get_generator
from ara.prompts.hypothesis_live import HypothesisGeneration, HypothesisItem
from ara.schemas import EntityRef, Provenance, Triple


def _triple() -> Triple:
    return Triple(
        subject=EntityRef(name="BRCA1", type="gene", id="brca1"),
        predicate="associated_with",
        object=EntityRef(name="Breast cancer", type="disease", id="breast_cancer"),
        confidence=0.9,
        provenance=Provenance(paper_id="PMID:1", chunk_id="0", span=0, extracted_by="test"),
    )


@pytest.mark.asyncio
async def test_mock_generator_static_and_derived() -> None:
    gen = MockGenerator()
    static = await gen.generate([])
    assert len(static) == 3 and static[0].id == "hyp_0"
    derived = await gen.generate([_triple()])
    assert len(derived) == 3
    assert "BRCA1" in derived[0].statement and "PMID:1" in derived[0].statement


def test_get_generator_factory() -> None:
    assert isinstance(get_generator("mock"), MockGenerator)
    assert isinstance(get_generator("live"), LLMGenerator)
    assert isinstance(get_generator(), MockGenerator)


@pytest.mark.asyncio
async def test_llm_generator_with_fake_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeStructured:
        def __init__(self, schema: type) -> None:
            self.schema = schema

        async def ainvoke(self, prompt: str) -> HypothesisGeneration:
            return HypothesisGeneration(
                hypotheses=[
                    HypothesisItem(
                        statement="BRCA1 loss sensitizes cells to PARP inhibition",
                        mechanism="synthetic lethality",
                        entities=["BRCA1", "PARP1"],
                        novelty_score=0.8,
                        plausibility_score=0.85,
                    )
                ]
            )

    class FakeLLM:
        model = "fake-model"

        def with_structured_output(self, schema: type) -> FakeStructured:
            return FakeStructured(schema)

    monkeypatch.setattr("ara.generators.llm.get_llm", lambda tier="reason": FakeLLM())
    gen = LLMGenerator()
    hyps = await gen.generate([_triple()], n=3)
    assert len(hyps) == 1
    assert hyps[0].statement.startswith("BRCA1 loss")
    assert hyps[0].entities == ["BRCA1", "PARP1"]
    assert hyps[0].status == "proposed"
