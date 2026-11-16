from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field


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

