from __future__ import annotations
from typing import List
from pydantic import BaseModel
from .hypothesis import Hypothesis

class ExperimentProposal(BaseModel):
    id: str
    hypothesis_id: str
    assay: str
    model_system: str
    controls: List[str]
    readouts: List[str]
    expected_outcomes: List[str]
    risks: List[str]
    citations: List[str]
