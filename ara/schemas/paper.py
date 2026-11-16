from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """A chunk of text extracted from a paper."""
    text: str
    paper_id: str
    span: int
    embedding: Optional[List[float]] = None


class Paper(BaseModel):
    """Domain model for a scientific paper."""
    id: str
    source: str  # e.g. "pubmed", "arxiv", "pdf"
    title: str
    abstract: str
    authors: List[str]
    year: int
    url: Optional[str] = None
    full_text: Optional[str] = None
    chunks: List[Chunk] = []
