from __future__ import annotations

from pydantic import BaseModel, Field

from .triple import Triple


class Hypothesis(BaseModel):
    """A scientific hypothesis derived from the knowledge graph."""

    id: str
    statement: str
    mechanism: str
    entities: list[str]  # list of entity IDs
    supporting: list[Triple] = []
    contradicting: list[Triple] = []
    novelty_score: float = Field(..., ge=0.0, le=1.0)
    plausibility_score: float = Field(..., ge=0.0, le=1.0)
    status: str = "proposed"
