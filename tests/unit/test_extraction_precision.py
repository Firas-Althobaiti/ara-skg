"""Unit tests for the over-prediction guard in LLMExtractor (issue #24)."""

from __future__ import annotations

import pytest

from ara.extractors import LLMExtractor
from ara.prompts.extraction_live import RELATIONS_PROMPT
from ara.schemas import Chunk
from ara.schemas.predicates import CANONICAL_PREDICATES


def _chunk() -> Chunk:
    return Chunk(text="BRCA1 and PARP inhibitors", paper_id="PMID:1", span=0)


def _stub_extractor(monkeypatch: pytest.MonkeyPatch, confidences: list[float]) -> LLMExtractor:
    from ara.prompts.extraction_live import EntityExtraction, RelationExtraction, RelationTriple

    class FakeStructured:
        def __init__(self, schema: type) -> None:
            self.schema = schema

        async def ainvoke(self, prompt: str) -> object:
            if self.schema is EntityExtraction:
                from ara.prompts.extraction_live import EntityMention

                return EntityExtraction(entities=[EntityMention(name="BRCA1", type="gene")])
            return RelationExtraction(
                triples=[
                    RelationTriple(
                        subject="BRCA1", predicate="causes", object=f"entity_{i}", confidence=c
                    )
                    for i, c in enumerate(confidences)
                ]
            )

    class FakeLLM:
        model = "fake-model"

        def with_structured_output(self, schema: type) -> FakeStructured:
            return FakeStructured(schema)

    monkeypatch.setattr("ara.extractors.llm.get_llm", lambda tier="fast": FakeLLM())
    return LLMExtractor()


@pytest.mark.asyncio
async def test_cap_keeps_at_most_max_relations(monkeypatch: pytest.MonkeyPatch) -> None:
    confidences = [0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5]
    ext = _stub_extractor(monkeypatch, confidences)
    result = await ext.extract_relations(_chunk(), [])
    assert len(result) <= 6  # MAX_RELATIONS_PER_CHUNK default
    assert len(result) == 6  # 8 passed the 0.6 floor, capped to 6
    assert all(t.confidence >= 0.6 for t in result)
    # highest confidence first
    assert [t.confidence for t in result] == sorted((t.confidence for t in result), reverse=True)


@pytest.mark.asyncio
async def test_low_confidence_triples_filtered(monkeypatch: pytest.MonkeyPatch) -> None:
    ext = _stub_extractor(monkeypatch, [0.5, 0.4, 0.3, 0.59])
    result = await ext.extract_relations(_chunk(), [])
    assert result == []


def test_prompt_lists_all_canonical_predicates_and_cap() -> None:
    for p in CANONICAL_PREDICATES:
        assert p in RELATIONS_PROMPT, f"canonical predicate {p!r} missing from RELATIONS_PROMPT"
    assert "If none fit the relation, do NOT emit a triple for it." in RELATIONS_PROMPT
    assert "Do NOT emit more than 6 triples per abstract" in RELATIONS_PROMPT
    assert "Quality over quantity" in RELATIONS_PROMPT
