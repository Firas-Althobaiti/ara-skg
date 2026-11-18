"""Graph-update nodes: resolve entities, ensure schema, upsert into the KG."""

from __future__ import annotations

from typing import Any

from ara.clients.kg import KnowledgeGraphClient
from ara.config import get_settings
from ara.schemas import ARAState, Triple, coerce_triple


def _client() -> KnowledgeGraphClient:
    """KG client injected via settings (monkeypatchable in tests)."""
    return get_settings().client


async def resolve_triples_node(state: ARAState) -> dict[str, Any]:
    """Resolve entity names of validated triples to canonical IDs.

    Conflicts are resolved by confidence: the highest-confidence occurrence
    of a (subject, predicate, object) key wins.
    """
    client = _client()
    valid = state.get("valid_triples", [])
    resolved: list[dict[str, Any]] = []
    best: dict[tuple[str, str, str], Triple] = {}
    for raw in valid:
        triple = coerce_triple(raw)
        key = (
            (triple.subject.id or triple.subject.name),
            triple.predicate,
            (triple.object.id or triple.object.name),
        )
        if key not in best or triple.confidence > best[key].confidence:
            best[key] = triple
    for triple in best.values():
        subj = await client.resolve_entity(triple.subject.name, triple.subject.type)
        obj = await client.resolve_entity(triple.object.name, triple.object.type)
        resolved.append(
            Triple(
                subject=subj,
                predicate=triple.predicate,
                object=obj,
                confidence=triple.confidence,
                provenance=triple.provenance,
            ).model_dump()
        )
    state["resolved_triples"] = resolved
    return {"resolved_triples": resolved}


async def ensure_schema_node(state: ARAState) -> dict[str, Any]:
    """Ensure the KG store schema is ready (no-op for NetworkX)."""
    await _client().ensure_schema()
    return {}


async def upsert_kg_node(state: ARAState) -> dict[str, Any]:
    """Batch-upsert validated triples into the KG; failures land in ``errors``."""
    client = _client()
    source = state.get("resolved_triples") or state.get("valid_triples", [])
    triples = [coerce_triple(t) for t in source]
    try:
        delta = await client.upsert_triples(triples)
    except Exception as exc:  # noqa: BLE001 - recorded, graph routes to rollback
        state["kg_delta"] = []
        state.setdefault("errors", []).append(str(exc))
        return {"kg_delta": [], "errors": state["errors"]}
    state["kg_delta"] = delta
    return {"kg_delta": delta}


async def rollback_on_error(state: ARAState) -> dict[str, Any]:
    """Compensating rollback: clear the delta of the failed batch."""
    state["kg_delta"] = []
    return {"kg_delta": []}


__all__ = [
    "resolve_triples_node",
    "ensure_schema_node",
    "upsert_kg_node",
    "rollback_on_error",
]
