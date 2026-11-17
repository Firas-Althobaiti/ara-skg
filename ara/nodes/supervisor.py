# File: ara/nodes/supervisor.py
"""Supervisor node – routes the current task to the appropriate subgraph."""

from typing import Any

from ara.state import ARAState


async def classify_intent_node(state: ARAState) -> dict[str, Any]:
    """
    Inspect the task description and decide which subgraph should handle it.
    Sets ``state['route'] to one of:
        ingestion | extraction | graph_update | query | hypothesis | experiment | evolution | end
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


async def critic_node(state: ARAState) -> dict[str, Any]:
    """
    Final grounding check – if errors are present, flag them for replanning.
    """
    if state.get("errors"):
        state["needs_replan"] = True
    return state


async def replan_node(state: ARAState) -> dict[str, Any]:
    """Re‑evaluate the plan; clear errors and route back to the supervisor."""
    state["errors"] = []
    state["needs_replan"] = False
    return state


__all__ = ["classify_intent_node", "critic_node", "replan_node"]
