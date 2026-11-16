from __future__ import annotations
from typing import List
from pydantic import BaseModel

class EvolutionEvent(BaseModel):
    window: str
    entity_id: str
    change_type: Literal["emerging", "fading", "renamed", "relation_shift"]
    before: str
    after: str
    evidence: List[str]
