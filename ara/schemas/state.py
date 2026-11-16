from __future__ import annotations

from typing import TypedDict, List, Dict, Optional
from .paper import Paper
from .entity import Entity
from .triple import Triple
from .hypothesis import Hypothesis
from .experiment import ExperimentProposal
from .evolution import EvolutionEvent


class ARAState(TypedDict, total=False):
    """Runtime state shared between LangGraph nodes."""
    messages: List[str]
    task: str
    intent: str
    papers: List[Paper]
    chunks: List[Dict]  # raw chunk dicts (text, metadata, optional embedding)
    extracted_triples: List[Dict]  # raw triple dicts before resolution
    resolved_triples: List[Dict]  # triples with canonical EntityRef IDs
    kg_delta: List[Dict]  # changes applied to the KG (add/remove)
    retrieved_subgraph: List[Dict]  # subgraph relevant to a query
    hypotheses: List[Hypothesis]
    experiments: List[ExperimentProposal]
    evolution_report: str
    critique: str
    errors: List[str]
    next_step: Optional[str]
    provenance: Dict[str, str]
    budget: Optional[float]

