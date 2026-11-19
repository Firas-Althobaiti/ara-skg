"""Live extraction prompts + structured-output schemas (issue #19).

NOTE: ``ara/prompts/extraction.py`` (legacy) is intentionally untouched —
these prompts are only used by the live LLM extractor.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ENTITY_TYPES = Literal["gene", "protein", "drug", "disease", "pathway", "phenotype", "other"]

# Standard biomedical relation inventory. Used BOTH as the prompt vocabulary and
# as a Literal type on RelationTriple.predicate, so structured output is
# grammar-constrained to this set (the model picks the closest one).
PREDICATES = (
    "involved_in",
    "associated_with",
    "causes",
    "predispose_to",
    "sensitizes",
    "sensitive_to",
    "induce",
    "kill",
    "binds_to",
    "attracts",
    "facilitates",
    "collapse",
    "restore",
    "is_a",
    "is_synthetically_lethal_in",
    "regulates",
    "inhibits",
    "activates",
    "part_of",
)
PREDICATE = Literal[
    "involved_in",
    "associated_with",
    "causes",
    "predispose_to",
    "sensitizes",
    "sensitive_to",
    "induce",
    "kill",
    "binds_to",
    "attracts",
    "facilitates",
    "collapse",
    "restore",
    "is_a",
    "is_synthetically_lethal_in",
    "regulates",
    "inhibits",
    "activates",
    "part_of",
]

ENTITIES_PROMPT = """You are an expert biomedical text miner. Extract every entity mention \
|(genes, proteins, drugs, diseases, pathways, phenotypes) from the abstract below.

IMPORTANT naming rules:
- Use the entity name EXACTLY as it appears in the text (same words, same capitalization
  for gene/protein symbols like PARP1 or BRCA1). Do not shorten "BRCA1 mutations" to "BRCA1".
- Include multi-word noun phrases ("homologous recombination", "gamma-H2AX foci") as one entity.

Abstract:
{text}

Return only the JSON object matching the required schema."""

RELATIONS_PROMPT = """You are a biomedical relation extractor. From the abstract below, extract \
EVERY relation triple (subject, predicate, object) that the text actually states. \
Aim for completeness — missing a stated relation hurts more than one extra triple.

Predicate rules (critical):
- Choose the predicate ONLY from this standard biomedical relation inventory:
  involved_in, associated_with, causes, predispose_to, sensitizes, sensitive_to,
  induce, kill, binds_to, attracts, facilitates, collapse, restore, is_a,
  is_synthetically_lethal_in, regulates, inhibits, activates, part_of.
- Map what the text says to the CLOSEST inventory predicate (e.g. "are acutely
  sensitive to" → sensitive_to; "trigger" → induce; "predispose" → predispose_to).
- Predicates must be lowercase snake_case, taken verbatim from the inventory.

Subject/object rules:
- Use the SHORTEST noun phrase from the text that names the entity exactly
  (e.g. "PARP inhibitors", not "treatment with PARP inhibitors"; "BRCA1 mutations",
  not "mutations in BRCA1"). Keep gene/protein symbols verbatim (PARP1, BRCA1).
- If one subject relates to several objects in one sentence, emit ONE triple per object.

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
    predicate: PREDICATE
    object: str
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class RelationExtraction(BaseModel):
    triples: list[RelationTriple]


__all__ = [
    "ENTITIES_PROMPT",
    "RELATIONS_PROMPT",
    "PREDICATES",
    "EntityMention",
    "EntityExtraction",
    "RelationTriple",
    "RelationExtraction",
]
