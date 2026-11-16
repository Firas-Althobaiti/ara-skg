from __future__ import annotations
from typing import List, Literal, Dict
from pydantic import BaseModel

class EntityRef(BaseModel):
    id: str | None = None
    name: str

class Entity(BaseModel):
    id: str
    canonical_name: str
    type: Literal["gene", "protein", "drug", "disease", "pathway", "phenotype", "other"]
    aliases: List[str] = []
    external_ids: Dict[str, str] = {}
