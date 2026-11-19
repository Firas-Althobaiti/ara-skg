"""Live hypothesis-generation prompt + structured-output schema (issue #19)."""

from __future__ import annotations

from pydantic import BaseModel, Field

HYPOTHESIS_PROMPT = """You are a biomedical research assistant. Based on the knowledge-graph \
triples below, propose {n} novel, testable scientific hypotheses. Each hypothesis needs a \
clear statement, a mechanism, the involved entities, and novelty/plausibility scores in [0, 1].

KG triples:
{context}

Return only the JSON object matching the required schema."""


class HypothesisItem(BaseModel):
    statement: str
    mechanism: str
    entities: list[str] = Field(default_factory=list)
    novelty_score: float = Field(default=0.5, ge=0.0, le=1.0)
    plausibility_score: float = Field(default=0.5, ge=0.0, le=1.0)


class HypothesisGeneration(BaseModel):
    hypotheses: list[HypothesisItem]


__all__ = ["HYPOTHESIS_PROMPT", "HypothesisItem", "HypothesisGeneration"]
