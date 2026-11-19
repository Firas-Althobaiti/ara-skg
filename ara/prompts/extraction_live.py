"""Live extraction prompts + structured-output schemas (issues #19, #24).

NOTE: ``ara/prompts/extraction.py`` (legacy) is intentionally untouched —
these prompts are only used by the live LLM extractor.

The predicate vocabulary is the canonical inventory from
:mod:`ara.schemas.predicates` (issue #24): the schema is a ``Literal`` over
those 20 verbs, so no non-canonical predicate can reach the pipeline.
"""

from __future__ import annotations

from typing import Literal, get_args

from pydantic import BaseModel, Field

from ara.schemas.predicates import CANONICAL_PREDICATES

ENTITY_TYPES = Literal["gene", "protein", "drug", "disease", "pathway", "phenotype", "other"]

# Grammar-constrained predicate type: exactly the canonical inventory.
# The assert keeps this Literal in sync with CANONICAL_PREDICATES.
PREDICATE = Literal[
    "associated_with",
    "causes",
    "treats",
    "inhibits",
    "activates",
    "encodes",
    "regulates",
    "binds",
    "interacts_with",
    "expressed_in",
    "expressed_by",
    "localized_to",
    "part_of",
    "regulates_expression_of",
    "phosphorylates",
    "methylates",
    "acetylates",
    "ubiquitinates",
    "targets",
    "involved_in",
]
assert set(get_args(PREDICATE)) == set(
    CANONICAL_PREDICATES
), "PREDICATE Literal drifted from CANONICAL_PREDICATES — keep them in sync"

PREDICATES = tuple(CANONICAL_PREDICATES)

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
relation triples (subject, predicate, object) that the text directly states.

CRITICAL: The paper's abstract typically contains 3-6 extractable relations. Do NOT emit \
more than 6 triples per abstract. If you find more candidates, keep only the 6 with \
highest confidence. Quality over quantity: a missed relation is better than a wrong one.

Predicate rules (critical):
Only emit predicates from this list: associated_with, causes, treats, inhibits, activates, \
encodes, regulates, binds, interacts_with, expressed_in, expressed_by, localized_to, \
part_of, regulates_expression_of, phosphorylates, methylates, acetylates, ubiquitinates, \
targets, involved_in. If none fit the relation, do NOT emit a triple for it.

Mapping hints (text phrase → canonical predicate):
- "induce / activate / upregulate / stimulate / promote / facilitate / restore" → activates
- "trigger / lead to / cause / result in / collapse" → causes
  (e.g. "BRCA2-deficient cells are acutely sensitive to PARP inhibitors" →
  (BRCA2-deficient cells, causes, PARP inhibitors))
- "sensitive to / sensitizes" → causes, with the object being the agent
- "block / inhibit / suppress / repress / prevent / kill" → inhibits
- "bind / attach" → binds; "attract / recruit / interact" → interacts_with
- "associated with / risk of / predispose to" → associated_with
- "is a / part of" → part_of; "involved in / essential in" → involved_in
- "encode" → encodes; "regulate" → regulates; "target" → targets; "treat" → treats

Subject/object rules:
- Use the SHORTEST noun phrase from the text that names the entity exactly
  (e.g. "PARP inhibitors", not "treatment with PARP inhibitors"; "BRCA1 mutations",
  not "mutations in BRCA1"). Keep gene/protein symbols verbatim (PARP1, BRCA1).
- If one subject relates to several objects in one sentence, emit ONE triple per object.
- Split coordinated objects: "induces gamma-H2AX and RAD51 foci" → TWO triples,
  (subject, predicate, gamma-H2AX foci) and (subject, predicate, RAD51 foci).
- Skip generic/meta statements ("represents a new concept", "may allow design of
  therapies") — only concrete biomedical relations count.
- Confidence: 0.9 only for relations the text states explicitly; 0.6-0.8 for implied
  ones. Never below 0.6.
- Prioritize relations about the key genes/proteins/drugs in the abstract and their
  direct effects (what inhibits/activates/causes what) over generic statements.

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
    "PREDICATE",
    "EntityMention",
    "EntityExtraction",
    "RelationTriple",
    "RelationExtraction",
]
