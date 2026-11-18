"""Supervisor nodes – route the task to a subgraph, then critic / replan."""

from __future__ import annotations

from typing import Any

from ara.schemas import ARAState


async def classify_intent_node(state: ARAState) -> dict[str, Any]:
    """Decide which subgraph handles ``state['task']``.

    Sets ``state['route']`` to one of:
    ingestion | extraction | graph_update | query | hypothesis | experiment |
    evolution | end
    """
    task = (state.get("task") or "").lower()
    if any(k in task for k in ("ingest", "fetch", "paper")):
        return {"route": "ingestion"}
    if "extract" in task:
        return {"route": "extraction"}
    if any(k in task for k in ("update", "upsert", "kg")):
        return {"route": "graph_update"}
    if "query" in task or "?" in task:
        return {"route": "query"}
    if "hypoth" in task:
        return {"route": "hypothesis"}
    if "experiment" in task:
        return {"route": "experiment"}
    if any(k in task for k in ("evol", "drift", "window")):
        return {"route": "evolution"}
    return {"route": "end"}


MAX_REPLANS = 3
"""Maximum number of replan cycles before the critic routes to END."""


async def critic_node(state: ARAState) -> dict[str, Any]:
    """Final grounding check – flag errors for replanning.

    The replan loop is bounded: when ``replan_count`` reaches
    :data:`MAX_REPLANS` the critic stops requesting a replan and lets the
    graph end with the errors preserved in state (instead of cycling until
    LangGraph raises ``GraphRecursionError``).
    """
    errors = state.get("errors") or []
    replan_count = state.get("replan_count", 0)
    needs_replan = bool(errors) and replan_count < MAX_REPLANS
    state["needs_replan"] = needs_replan
    return {"needs_replan": needs_replan}


async def replan_node(state: ARAState) -> dict[str, Any]:
    """Count this replan cycle; errors are preserved (not cleared).

    The task is left unchanged so the supervisor re-routes to the same
    subgraph; the bounded :func:`critic_node` eventually ends the run.
    """
    count = state.get("replan_count", 0) + 1
    state["replan_count"] = count
    state["needs_replan"] = False
    return {"replan_count": count, "needs_replan": False}


# Short aliases listed in ``ara.nodes.__all__``.
classify_intent = classify_intent_node
critic_check = critic_node
replan_task = replan_node


__all__ = [
    "MAX_REPLANS",
    "classify_intent_node",
    "critic_node",
    "replan_node",
    "classify_intent",
    "critic_check",
    "replan_task",
]
