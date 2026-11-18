from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .entity import EntityRef


class Provenance(BaseModel):
    """Provenance information for a extracted triple."""

    paper_id: str
    chunk_id: str
    span: int
    extracted_by: str


class Triple(BaseModel):
    """Typed triple representing a relationship between entities."""

    subject: EntityRef
    predicate: str
    object: EntityRef
    confidence: float = Field(..., ge=0.0, le=1.0)
    provenance: Provenance


def coerce_triple(triple: Triple | dict[str, Any]) -> Triple:
    """Return *triple* as a :class:`Triple` model.

    Nodes in ``ara.nodes`` store triples in the state either as ``Triple``
    models or as plain dicts (``model_dump()``).  This helper normalises both
    representations so every consumer can rely on attribute access.
    """
    if isinstance(triple, Triple):
        return triple
    return Triple.model_validate(triple)


def triple_to_dict(triple: Triple | dict[str, Any]) -> dict[str, Any]:
    """Return *triple* as a plain dict (safe for both models and dicts)."""
    if isinstance(triple, Triple):
        return triple.model_dump()
    return dict(triple)
