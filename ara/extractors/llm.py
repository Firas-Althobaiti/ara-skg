"""Live LLM extractor: uses ``get_llm("fast")`` with structured outputs.

Prompts live in :mod:`ara.prompts.extraction_live` (the legacy
``ara/prompts/extraction.py`` prompts are untouched). Responses can be
cached on disk via ``EVAL_CACHE=1`` (see :mod:`ara.eval._llm_cache`) so
repeated live evals stay under the cost cap.
"""

from __future__ import annotations

import json
from typing import Any, TypeVar, cast

from pydantic import BaseModel

from ara.llm import get_llm
from ara.prompts.extraction_live import (
    ENTITIES_PROMPT,
    RELATIONS_PROMPT,
    EntityExtraction,
    RelationExtraction,
)
from ara.schemas import Chunk, Entity, EntityRef, Provenance, Triple

from .base import Extractor

T = TypeVar("T", bound=BaseModel)


class LLMExtractor:
    """LLM-backed :class:`Extractor` (requires ``OPENAI_API_KEY``)."""

    def __init__(self, tier: Any = "fast") -> None:
        self._tier = tier
        self._llm: Any = None

    def _get_llm(self) -> Any:
        if self._llm is None:
            self._llm = get_llm(self._tier)
        return self._llm

    async def _invoke(self, schema: type[T], prompt: str) -> T:
        from ara.eval._llm_cache import cache_enabled, cache_get, cache_set

        llm = self._get_llm()
        model = str(getattr(llm, "model", "unknown"))
        if cache_enabled():
            hit = cache_get(prompt, model)
            if hit is not None:
                return schema.model_validate(json.loads(hit))
        chain = llm.with_structured_output(schema)
        result = await chain.ainvoke(prompt)
        if cache_enabled():
            cache_set(prompt, model, result.model_dump_json())
        return cast(T, result)

    async def extract_entities(self, chunk: Chunk) -> list[Entity]:
        result = await self._invoke(EntityExtraction, ENTITIES_PROMPT.format(text=chunk.text))
        return [
            Entity(
                id=e.name,
                canonical_name=e.name,
                type=e.type,
                aliases=e.aliases,
            )
            for e in result.entities
        ]

    async def extract_relations(self, chunk: Chunk, entities: list[Entity]) -> list[Triple]:
        entity_names = ", ".join(e.canonical_name for e in entities) or "(none)"
        prompt = RELATIONS_PROMPT.format(text=chunk.text, entities=entity_names)
        result = await self._invoke(RelationExtraction, prompt)
        triples: list[Triple] = []
        for t in result.triples:
            triples.append(
                Triple(
                    subject=EntityRef(name=t.subject, type="other", id=t.subject),
                    predicate=t.predicate,
                    object=EntityRef(name=t.object, type="other", id=t.object),
                    confidence=max(0.0, min(1.0, t.confidence)),
                    provenance=Provenance(
                        paper_id=chunk.paper_id,
                        chunk_id=str(chunk.span),
                        span=0,
                        extracted_by="llm_extractor",
                    ),
                )
            )
        return triples


__all__ = ["LLMExtractor", "Extractor"]
