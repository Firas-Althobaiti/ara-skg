from __future__ import annotations
from typing import List
from pydantic import BaseModel, Field
from .entity import EntityRef

class Provenance(BaseModel):
    paper_id: str
    chunk_id: str
    span: int
    extracted_by: str

class Triple(BaseModel):
    subject: EntityRef
    predicate: str
    object: EntityRef
    confidence: float = Field(..., ge=0.0, le=1.0)
    provenance: Provenance
