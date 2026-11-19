"""Extractor protocol: turn a text chunk into entities and triples."""

from __future__ import annotations

from typing import Protocol

from ara.schemas import Chunk, Entity, Triple


class Extractor(Protocol):
    """Strategy interface for entity/relation extraction."""

    async def extract_entities(self, chunk: Chunk) -> list[Entity]:
        """Extract entity mentions from *chunk*."""
        ...

    async def extract_relations(self, chunk: Chunk, entities: list[Entity]) -> list[Triple]:
        """Extract relation triples from *chunk*, given the known *entities*."""
        ...
