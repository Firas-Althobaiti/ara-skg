"""Unit tests for the extraction strategies (issue #19)."""

from __future__ import annotations

import pytest

from ara.extractors import LLMExtractor, MockExtractor, get_extractor
from ara.prompts.extraction_live import (
    EntityExtraction,
    EntityMention,
    RelationExtraction,
    RelationTriple,
)
from ara.schemas import Chunk


def _chunk(text: str, paper_id: str = "PMID:1") -> Chunk:
    return Chunk(text=text, paper_id=paper_id, span=0)


@pytest.mark.asyncio
async def test_mock_extractor_matches_legacy_behavior() -> None:
    ext = MockExtractor()
    ents = await ext.extract_entities(_chunk("BRCA1, TP53, PARP1"))
    assert [e.canonical_name for e in ents] == ["BRCA1", "TP53", "PARP1"]

    rels = await ext.extract_relations(
        _chunk("BRCA1 - associated_with - Breast cancer; TP53 - regulates - BRCA1"), []
    )
    assert [(t.subject.name, t.predicate, t.object.name) for t in rels] == [
        ("BRCA1", "associated_with", "Breast cancer"),
        ("TP53", "regulates", "BRCA1"),
    ]
    assert all(t.confidence == 0.9 for t in rels)
    assert all(t.provenance.paper_id == "PMID:1" for t in rels)


def test_get_extractor_factory() -> None:
    assert isinstance(get_extractor("mock"), MockExtractor)
    assert isinstance(get_extractor("live"), LLMExtractor)
    assert isinstance(get_extractor(), MockExtractor)  # default


@pytest.mark.asyncio
async def test_llm_extractor_with_fake_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLMExtractor returns well-shaped models from a stubbed LLM (no network)."""

    class FakeStructured:
        def __init__(self, schema: type) -> None:
            self.schema = schema

        async def ainvoke(self, prompt: str) -> object:
            if self.schema is EntityExtraction:
                return EntityExtraction(entities=[EntityMention(name="BRCA1", type="gene")])
            return RelationExtraction(
                triples=[
                    RelationTriple(
                        subject="BRCA1",
                        predicate="associated_with",
                        object="breast cancer",
                        confidence=0.9,
                    )
                ]
            )

    class FakeLLM:
        model = "fake-model"

        def with_structured_output(self, schema: type) -> FakeStructured:
            return FakeStructured(schema)

    monkeypatch.setattr("ara.extractors.llm.get_llm", lambda tier="fast": FakeLLM())
    ext = LLMExtractor()
    ents = await ext.extract_entities(_chunk("BRCA1 and breast cancer", paper_id="PMID:9"))
    assert ents[0].canonical_name == "BRCA1" and ents[0].type == "gene"
    rels = await ext.extract_relations(
        _chunk("BRCA1 linked to breast cancer", paper_id="PMID:9"), ents
    )
    assert rels[0].predicate == "associated_with"
    assert rels[0].provenance.paper_id == "PMID:9"
    assert rels[0].confidence == 0.9
