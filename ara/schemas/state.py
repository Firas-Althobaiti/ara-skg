from __future__ import annotations
from typing import TypedDict, List, Dict, Optional
from .paper import Paper
from .entity import Entity
from .triple import Triple
from .hypothesis import Hypothesis
from .experiment import ExperimentProposal
from .evolution import EvolutionEvent

class ARAState(TypedDict, total=False):
    messages: List[str]
    task: str
    intent: str
    papers: List[Paper]
    chunks: List[dict]  # raw chunk dicts
    extracted_triples: List[dict]
    resolved_triples: List[dict]
    kg_delta: List[dict]
    retrieved_subgraph: List[dict]
    hypotheses: List[Hypothesis]
    experiments: List[ExperimentProposal]
    evolution_report: str
    critique: str
    errors: List[str]
    next_step: Optional[str]
    provenance: Dict[str, str]
    budget: Optional[float]
