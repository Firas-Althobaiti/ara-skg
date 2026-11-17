from __future__ import annotations

from typing import TypedDict

from .experiment import ExperimentProposal
from .hypothesis import Hypothesis
from .paper import Paper


class ARAState(TypedDict, total=False):
    """Runtime state shared between LangGraph nodes."""

    messages: list[str]
    task: str
    intent: str
    papers: list[Paper]
    chunks: list[dict]  # raw chunk dicts (text, metadata, optional embedding)
    extracted_triples: list[dict]  # raw triple dicts before resolution
    resolved_triples: list[dict]  # triples with canonical EntityRef IDs
    kg_delta: list[dict]  # changes applied to the KG (add/remove)
    retrieved_subgraph: list[dict]  # subgraph relevant to a query
    hypotheses: list[Hypothesis]
    experiments: list[ExperimentProposal]
    evolution_report: str
    critique: str
    errors: list[str]
    next_step: str | None
    provenance: dict[str, str]
    budget: float | None
