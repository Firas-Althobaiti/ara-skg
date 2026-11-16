from __future__ import annotations
from typing import List
from pydantic import BaseModel, Field
from .triple import Triple

class Hypothesis(BaseModel):
    id: str
    statement: str
    mechanism: str
    entities: List[str]  # list of entity IDs
    supporting: List[Triple] = []
    contradicting: List[Triple] = []
    novelty_score: float = Field(..., ge=0.0, le=1.0)
    plausibility_score: float = Field(..., ge=0.0, le=1.0)
    status: str = "proposed"
