from __future__ import annotations

from pydantic import BaseModel


class Chunk(BaseModel):
    """A chunk of text extracted from a paper."""

    text: str
    paper_id: str
    span: int
    embedding: list[float] | None = None


class Paper(BaseModel):
    """Domain model for a scientific paper."""

    id: str
    source: str  # e.g. "pubmed", "arxiv", "pdf"
    title: str
    abstract: str
    authors: list[str]
    year: int
    url: str | None = None
    full_text: str | None = None
    chunks: list[Chunk] = []
