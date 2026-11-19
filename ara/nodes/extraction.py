"""Extraction nodes: entities → relations → linking → validation (critic).

Text is mined with a deterministic extractor that doubles as the *mocked LLM*
when no ``OPENAI_API_KEY`` is configured: chunks are expected to contain
``"Subject - predicate - Object; ..."`` segments (comma-separated entity
lists for :func:`extract_entities_node`).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from ara.clients.entity_linking import DEV_ALIAS_MAP, EntityLinkingClient
from ara.config import get_settings
from ara.extractors import get_extractor
from ara.logging import get_logger
from ara.schemas import ARAState, Chunk, EntityRef, coerce_triple
from ara.schemas.predicates import canonicalize


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Attribute-or-key access for models and dicts alike."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _papers_chunks(state: ARAState) -> Iterator[tuple[str, Any]]:
    """Yield ``(paper_id, chunk)`` pairs for every chunk of every paper."""
    for paper in state.get("papers", []):
        paper_id = _get(paper, "id", "")
        for chunk in _get(paper, "chunks", []) or []:
            yield paper_id, chunk


def _as_chunk(chunk: Any) -> Chunk:
    return chunk if isinstance(chunk, Chunk) else Chunk.model_validate(chunk)


def _extractor() -> Any:
    """Active extractor from settings; logs a one-liner in live mode (cost!)."""
    mode = get_settings().EXTRACTION_MODE
    if mode == "live":
        get_logger("ara.extraction").info(
            "live extraction mode — LLM calls incur cost", mode="live"
        )
    return get_extractor(mode)


async def extract_entities_node(state: ARAState) -> dict[str, Any]:
    """Extract entity mentions from each chunk via the configured extractor."""
    extractor = _extractor()
    extracted: list[dict[str, Any]] = []
    for paper_id, chunk in _papers_chunks(state):
        text = _get(chunk, "text", "") or ""
        for ent in await extractor.extract_entities(_as_chunk(chunk)):
            entity_ref = EntityRef(
                name=ent.canonical_name, type=ent.type, id=ent.id or ent.canonical_name
            )
            extracted.append(
                {"entity": entity_ref, "source_chunk": text[:30], "paper_id": paper_id}
            )
    state["extracted_entities"] = extracted
    return {"extracted_entities": extracted}


async def extract_relations_node(state: ARAState) -> dict[str, Any]:
    """Extract triples from chunk text via the configured extractor.

    The result is stored as plain dicts (``Triple.model_dump()``) in
    ``state['extracted_triples']``; the mock extractor uses a fixed
    confidence of 0.9.
    """
    extractor = _extractor()
    triples: list[dict[str, Any]] = []
    for _paper_id, chunk in _papers_chunks(state):
        chunk_model = _as_chunk(chunk)
        entities = await extractor.extract_entities(chunk_model)
        for triple in await extractor.extract_relations(chunk_model, entities):
            dumped = triple.model_dump()
            # Canonicalize the predicate (issue #24): verbose surface forms
            # map onto the canonical 20-verb inventory before storage/eval.
            dumped["predicate"] = canonicalize(str(dumped["predicate"]))
            triples.append(dumped)
    state["extracted_triples"] = triples
    return {"extracted_triples": triples}


async def link_entities_node(state: ARAState) -> dict[str, Any]:
    """Resolve entity names to canonical IDs using the EntityLinkingClient."""
    if get_settings().LINKING_MODE == "alias":
        get_logger("ara.linking").warning(
            "fake alias map active — dev-only, do not use in production"
        )
        linker = EntityLinkingClient(alias_map=DEV_ALIAS_MAP)
    else:
        linker = EntityLinkingClient()  # no-op by default
    extracted = state.get("extracted_entities", [])
    linked: list[dict[str, Any]] = []
    for ent in extracted:
        raw = ent["entity"] if isinstance(ent, dict) else ent
        entity_ref = raw if isinstance(raw, EntityRef) else EntityRef.model_validate(raw)
        resolved = await linker.link_entity(entity_ref.name, entity_ref.type)
        linked.append({"entity": resolved, "source": entity_ref.name})
    state["linked_entities"] = linked
    return {"linked_entities": linked}


async def validate_triples_node(state: ARAState) -> dict[str, Any]:
    """Critic: keep only triples with confidence >= 0.7 and valid provenance."""
    valid: list[Any] = []
    for triple in state.get("extracted_triples", []):
        t = coerce_triple(triple)
        if t.confidence >= 0.7 and t.provenance is not None:
            valid.append(triple)
    state["valid_triples"] = valid
    return {"valid_triples": valid}


__all__ = [
    "extract_entities_node",
    "extract_relations_node",
    "link_entities_node",
    "validate_triples_node",
]
