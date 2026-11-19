"""Live extraction prompts + structured-output schemas (issue #19).

NOTE: ``ara/prompts/extraction.py`` (legacy) is intentionally untouched —
these prompts are only used by the live LLM extractor.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ENTITY_TYPES = Literal["gene", "protein", "drug", "disease", "pathway", "phenotype", "other"]

ENTITIES_PROMPT = """You are an expert biomedical text miner. Extract every entity mention \
(genes, proteins, drugs, diseases, pathways, phenotypes) from the abstract below.

Abstract:
{text}

Return only the JSON object matching the required schema."""

RELATIONS_PROMPT = """You are a biomedical relation extractor. From the abstract below, extract \
relation triples (subject, predicate, object) that the text actually states. \
Prefer the entities listed, but you may introduce others explicitly mentioned.
Use short snake_case predicates. Give each triple a confidence in [0, 1].

Abstract:
{text}

Known entities: {entities}

Return only the JSON object matching the required schema."""


class EntityMention(BaseModel):
    name: str
    type: ENTITY_TYPES = "other"
    aliases: list[str] = Field(default_factory=list)


class EntityExtraction(BaseModel):
    entities: list[EntityMention]


class RelationTriple(BaseModel):
    subject: str
    predicate: str
    object: str
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class RelationExtraction(BaseModel):
    triples: list[RelationTriple]


__all__ = [
    "ENTITIES_PROMPT",
    "RELATIONS_PROMPT",
    "EntityMention",
    "EntityExtraction",
    "RelationTriple",
    "RelationExtraction",
]
