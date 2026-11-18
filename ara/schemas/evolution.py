from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class EvolutionEvent(BaseModel):
    """A change observed in the knowledge graph over a time window."""

    window: str
    entity_id: str
    change_type: Literal["emerging", "fading", "renamed", "relation_shift"]
    before: str
    after: str
    evidence: list[str]
