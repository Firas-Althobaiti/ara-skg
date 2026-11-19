"""Mock extractor: the deterministic parser, moved verbatim from
``ara/nodes/extraction.py`` (no behavior change).

Chunks are expected to contain ``"Subject - predicate - Object; ..."``
segments (entities: comma-separated names). This doubles as the mocked LLM
when ``EXTRACTION_MODE=mock`` (the default, CI-safe).
"""

from __future__ import annotations

from ara.schemas import Chunk, Entity, EntityRef, Provenance, Triple

from .base import Extractor


class MockExtractor:
    """Deterministic regex-free parser implementing :class:`Extractor`."""

    async def extract_entities(self, chunk: Chunk) -> list[Entity]:
        names = [n.strip() for n in chunk.text.split(",") if n.strip()]
        return [Entity(id=n, canonical_name=n, type="other") for n in names]

    async def extract_relations(self, chunk: Chunk, entities: list[Entity]) -> list[Triple]:
        triples: list[Triple] = []
        parts = [p.strip() for p in chunk.text.split(";") if p.strip()]
        for part in parts:
            segments = [s.strip() for s in part.split("-") if s.strip()]
            if len(segments) == 3:
                subj, pred, obj = segments
                triples.append(
                    Triple(
                        subject=EntityRef(name=subj, type="other", id=subj),
                        predicate=pred,
                        object=EntityRef(name=obj, type="other", id=obj),
                        confidence=0.9,
                        provenance=Provenance(
                            paper_id=chunk.paper_id,
                            chunk_id=str(chunk.span),
                            span=0,
                            extracted_by="mock_extractor",
                        ),
                    )
                )
        return triples


__all__ = ["MockExtractor", "Extractor"]
