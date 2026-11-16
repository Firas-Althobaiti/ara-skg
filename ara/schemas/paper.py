from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field

class Chunk(BaseModel):
    text: str
    paper_id: str
    span: int
    embedding: Optional[List[float]] = None

class Paper(BaseModel):
    id: str
    source: str
    title: str
    abstract: str
    authors: List[str]
    year: int
    url: Optional[str] = None
    full_text: Optional[str] = None
    chunks: List[Chunk] = []
