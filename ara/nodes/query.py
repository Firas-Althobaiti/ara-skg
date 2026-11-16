from typing import Dict, Any, List
from ara.state import ARAState
from ara.config import get_settings
from ara.clients.kg_neo4j import Neo4jKnowledgeGraphClient
import asyncio
import time

async def classify_query(state: ARAState) -> Dict[str, Any]:
    """
    Very simple intent classifier: if the task contains a question mark,
    treat it as a query; otherwise treat as a generic task.
    """
    intent = "query" if "?" in state.get("task", "") else "generic"
    state["intent"] = intent
    return state


async def nl2cypher_node(state: ARAState) -> Dict[str, Any]:
    """
    Very naive NL‑to‑Cypher translator.
    - If the intent is "query", generate a simple pattern that matches all entities.
    - Otherwise return an empty pattern.
    """
    if state.get("intent") != "query":
        return state

    # naive pattern: match all entities and return their names
    cypher = "MATCH (n:Entity) RETURN n.name AS name, n.id AS id"
    params = {}
    state["cypher"] = cypher
    state["params"] = params
    return state


async def guard_cypher_node(state: ARAState) -> Dict[str, Any]:
    """
    Reject queries that contain write‑operation keywords.
    """
    cypher = state.get("cypher", "")
    write_keywords = ["CREATE", "DELETE", "MERGE", "SET", "WITH", "EXECUTE"]
    if any(kw.upper() in cypher.upper() for kw in write_keywords):
        state["error"] = "write operation not allowed"
        return state
    return state


async def run_cypher_node(state: ARAState) -> Dict[str, Any]:
    """
    Execute the Cypher query using the Neo4j client.
    For demonstration we return dummy rows.
    """
    client: Neo4jKnowledgeGraphClient = get_settings().client
    cypher = state.get("cypher", "")
    params = state.get("params", {})
    start = time.time()
    try:
        result = await client.query_cypher(cypher, params)
    except Exception as exc:
        result = [{"error": str(exc)}]
    runtime = round(time.time() - start, 3)
    state["run_result"] = {"result": result, "runtime": runtime}
    return state


async def synthesize_answer_node(state: ARAState) -> Dict[str, Any]:
    """
    Combine subgraph context (if any) with the query result to produce a final answer.
    """
    # In a real system we would pull the relevant subgraph nodes and vector search results.
    # For this demo we just join the raw result rows into a short sentence.
    result_data = state.get("run_result", {}).get("result", [])
    if not result_data:
        answer = "No information found."
    else:
        # join the first few rows into a readable string
        rows = [f"{row['name']}: {row.get('description', '')}" for row in result_data[:3]]
        answer = "Found: " + "; ".join(rows)
    state["final_answer"] = answer
    return state
