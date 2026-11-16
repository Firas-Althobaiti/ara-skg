# File: ara/nodes/evolution.py
from typing import Dict, Any, List
from ara.state import ARAState
from collections import Counter
import asyncio

async def window_triples_node(state: ARAState) -> Dict[str, Any]:
    """
    Return the triples for the current time window.
    In this simple implementation the current window is `valid_triples`
    and the previous window is `prev_valid_triples`.
    """
    return state

def _key(triple: Dict[str, Any]):
    return (triple["subject"]["id"], triple["predicate"], triple["object"]["id"])

async def detect_changes_node(state: ARAState) -> Dict[str, Any]:
    """
    Detect emerging, fading, and relation_shift events between the
    previous and current windows.
    """
    current = state.get("valid_triples", [])
    previous = state.get("prev_valid_triples", [])

    current_set = {_key(t) for t in current}
    previous_set = {_key(t) for t in previous}

    events: List[Dict[str, Any]] = []

    # Emerging: present now, absent before
    for t in current:
        if _key(t) not in previous_set:
            events.append({
                "window": "current",
                "entity_id": t["subject"]["id"],
                "change_type": "emerging",
                "before": "",
                "after": t["predicate"],
                "evidence": [t.get("provenance", {})],
            })

    # Fading: present before, absent now
    for t in previous:
        if _key(t) not in current_set:
            events.append({
                "window": "previous",
                "entity_id": t["subject"]["id"],
                "change_type": "fading",
                "before": t["predicate"],
                "after": "",
                "evidence": [t.get("provenance", {})],
            })

    # Relation shift: predicate distribution change > 50 %
    cur_pred = Counter(t["predicate"] for t in current)
    prev_pred = Counter(t["predicate"] for t in previous)
    all_preds = set(cur_pred) | set(prev_pred)
    for pred in all_preds:
        cur_count = cur_pred.get(pred, 0)
        prev_count = prev_pred.get(pred, 0)
        total = max(cur_count + prev_count, 1)
        diff = abs(cur_count - prev_count) / total
        if diff > 0.5:
            events.append({
                "window": "current",
                "entity_id": None,
                "change_type": "relation_shift",
                "before": f"prev_count={prev_count}",
                "after": f"cur_count={cur_count}",
                "evidence": [],
            })

    state["evolution_events"] = events
    return state

async def summarize_evolution_node(state: ARAState) -> Dict[str, Any]:
    """Produce a markdown report from the detected evolution events."""
    events = state.get("evolution_events", [])
    if not events:
        report = "No evolution events detected."
    else:
        lines = ["## Evolution Summary\n"]
        for ev in events:
            lines.append(
                f"- **{ev['change_type']}**: {ev['before']} → {ev['after']} "
                f"(entity: {ev['entity_id']})"
            )
        report = "\n".join(lines)
    state["evolution_report"] = report
    return state

__all__ = ["window_triples_node", "detect_changes_node", "summarize_evolution_node"]
