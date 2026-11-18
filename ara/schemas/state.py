from __future__ import annotations

from typing import Any, TypedDict

from .experiment import ExperimentProposal
from .hypothesis import Hypothesis
from .paper import Paper


class ARAState(TypedDict, total=False):
    """Runtime state shared between LangGraph nodes.

    Nodes return partial updates (plain dicts) which LangGraph merges into
    this state.  Triple-carrying keys hold either ``Triple`` models or their
    ``model_dump()`` dicts — use :func:`ara.schemas.coerce_triple` /
    :func:`ara.schemas.triple_to_dict` to normalise them.
    """

    messages: list[str]
    task: str
    intent: str
    source: str
    route: str
    papers: list[Paper]
    chunks: list[dict]  # raw chunk dicts (text, metadata, optional embedding)
    extracted_entities: list[dict]
    linked_entities: list[dict]
    extracted_triples: list[dict]  # raw triple dicts before resolution
    valid_triples: list[Any]  # validated triples (Triple models or dicts)
    prev_valid_triples: list[Any]  # triples from the previous evolution window
    resolved_triples: list[dict]  # triples with canonical EntityRef IDs
    kg_delta: list[dict] | dict[str, Any]  # changes applied to the KG (add/remove)
    retrieved_subgraph: list[dict]  # subgraph relevant to a query
    cypher: str
    params: dict
    run_result: dict  # {"result": [...], "runtime": float}
    final_answer: str
    hypotheses: list[Hypothesis]
    experiments: list[ExperimentProposal]
    experiment: Any  # single latest ExperimentProposal (model or dict)
    experiment_error: str | None
    evolution_events: list[dict]
    evolution_report: str
    critique: str
    critique_error: str | None
    evolution_error: str | None
    error: str | None
    errors: list[str]
    next_step: str | None
    needs_replan: bool
    provenance: dict[str, str]
    budget: float | None
