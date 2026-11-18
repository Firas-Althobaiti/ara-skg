"""Query nodes: classify intent → NL2Cypher → guard → run → synthesize."""

from __future__ import annotations

import time
from typing import Any

from ara.config import get_settings
from ara.schemas import ARAState


async def classify_query_node(state: ARAState) -> dict[str, Any]:
    """Intent classifier: a ``?`` in the task means a read query."""
    intent = "query" if "?" in state.get("task", "") else "generic"
    state["intent"] = intent
    return {"intent": intent}


# Backwards-compatible alias (older scripts imported ``classify_query``).
classify_query = classify_query_node


async def nl2cypher_node(state: ARAState) -> dict[str, Any]:
    """Naive NL→Cypher translator (mocked LLM): one read-only pattern."""
    if state.get("intent") != "query":
        state["cypher"] = ""
        state["params"] = {}
        return {"cypher": "", "params": {}}
    cypher = "MATCH (n:Entity) RETURN n.name AS name, n.id AS id"
    params: dict[str, Any] = {}
    state["cypher"] = cypher
    state["params"] = params
    return {"cypher": cypher, "params": params}


# Alias matching the ``*_node`` naming convention.
nl2cypher = nl2cypher_node


async def guard_cypher_node(state: ARAState) -> dict[str, Any]:
    """Reject queries that contain write-operation keywords."""
    cypher = state.get("cypher", "")
    write_keywords = ["CREATE", "DELETE", "MERGE", "SET", "WITH", "EXECUTE"]
    if any(kw in cypher.upper() for kw in write_keywords):
        state["error"] = "write operation not allowed"
        return {"error": "write operation not allowed"}
    state.pop("error", None)
    return {}


guard_cypher = guard_cypher_node


async def run_cypher_node(state: ARAState) -> dict[str, Any]:
    """Execute the (guarded) Cypher query against the configured KG client."""
    client = get_settings().client
    cypher = state.get("cypher", "")
    params = state.get("params", {})
    start = time.time()
    try:
        result = await client.query_cypher(cypher, params)
    except Exception as exc:  # noqa: BLE001 - surfaced as an error row
        result = [{"error": str(exc)}]
    runtime = round(time.time() - start, 3)
    run_result = {"result": result, "runtime": runtime}
    state["run_result"] = run_result
    return {"run_result": run_result}


run_cypher = run_cypher_node


async def synthesize_answer_node(state: ARAState) -> dict[str, Any]:
    """Combine the query result rows into a short evidence-backed answer."""
    result_data = state.get("run_result", {}).get("result", [])
    if not result_data:
        answer = "No information found."
    else:
        rows = [f"{row.get('name', '')}: {row.get('description', '')}" for row in result_data[:3]]
        answer = "Found: " + "; ".join(rows)
    state["final_answer"] = answer
    return {"final_answer": answer}


synthesize_answer = synthesize_answer_node


__all__ = [
    "classify_query_node",
    "classify_query",
    "nl2cypher_node",
    "nl2cypher",
    "guard_cypher_node",
    "guard_cypher",
    "run_cypher_node",
    "run_cypher",
    "synthesize_answer_node",
    "synthesize_answer",
]
