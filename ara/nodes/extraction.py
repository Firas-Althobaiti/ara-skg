"""Extraction nodes: entities → relations → linking → validation (critic).

Text is mined with a deterministic extractor that doubles as the *mocked LLM*
when no ``OPENAI_API_KEY`` is configured: chunks are expected to contain
``"Subject - predicate - Object; ..."`` segments (comma-separated entity
lists for :func:`extract_entities_node`).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from ara.clients.entity_linking import EntityLinkingClient
from ara.schemas import ARAState, EntityRef, Provenance, Triple, coerce_triple


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


async def extract_entities_node(state: ARAState) -> dict[str, Any]:
    """Extract entity mentions from each chunk (comma-separated names)."""
    extracted: list[dict[str, Any]] = []
    for paper_id, chunk in _papers_chunks(state):
        text = _get(chunk, "text", "") or ""
        names = [n.strip() for n in text.split(",") if n.strip()]
        for name in names:
            entity_ref = EntityRef(name=name, type="other", id=name)
            extracted.append(
                {"entity": entity_ref, "source_chunk": text[:30], "paper_id": paper_id}
            )
    state["extracted_entities"] = extracted
    return {"extracted_entities": extracted}


async def extract_relations_node(state: ARAState) -> dict[str, Any]:
    """Extract triples from chunk text (``"subj - pred - obj; ..."``).

    The result is stored as plain dicts (``Triple.model_dump()``) in
    ``state['extracted_triples']`` with a fixed mock confidence of 0.9.
    """
    triples: list[dict[str, Any]] = []
    for paper_id, chunk in _papers_chunks(state):
        text = _get(chunk, "text", "") or ""
        span = _get(chunk, "span", 0)
        parts = [p.strip() for p in text.split(";") if p.strip()]
        for part in parts:
            segments = [s.strip() for s in part.split("-") if s.strip()]
            if len(segments) == 3:
                subj, pred, obj = segments
                triple = Triple(
                    subject=EntityRef(name=subj, type="other", id=subj),
                    predicate=pred,
                    object=EntityRef(name=obj, type="other", id=obj),
                    confidence=0.9,
                    provenance=Provenance(
                        paper_id=paper_id,
                        chunk_id=str(span),
                        span=0,
                        extracted_by="extract_relations_node",
                    ),
                )
                triples.append(triple.model_dump())
    state["extracted_triples"] = triples
    return {"extracted_triples": triples}


async def link_entities_node(state: ARAState) -> dict[str, Any]:
    """Resolve entity names to canonical IDs using the EntityLinkingClient."""
    linker = EntityLinkingClient()
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
