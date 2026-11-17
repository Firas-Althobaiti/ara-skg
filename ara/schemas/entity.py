from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class EntityRef(BaseModel):
    """Reference to an entity – either by canonical ID or by name."""

    id: str | None = None
    name: str


class Entity(BaseModel):
    """Canonical representation of a scientific entity."""

    id: str
    canonical_name: str
    type: Literal[
        "gene",
        "protein",
        "drug",
        "disease",
        "pathway",
        "phenotype",
        "other",
    ]
    aliases: list[str] = []
    external_ids: dict[str, str] = {}
