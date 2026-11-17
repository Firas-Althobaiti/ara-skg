from __future__ import annotations

from pydantic import BaseModel


class ExperimentProposal(BaseModel):
    """A proposed experimental design linked to a hypothesis."""

    id: str
    hypothesis_id: str
    assay: str
    model_system: str
    controls: list[str]
    readouts: list[str]
    expected_outcomes: list[str]
    risks: list[str]
    citations: list[str]
