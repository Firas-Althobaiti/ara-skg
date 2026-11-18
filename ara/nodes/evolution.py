"""Evolution nodes: window → detect changes → summarize into a report."""

from __future__ import annotations

from collections import Counter
from typing import Any

from ara.schemas import ARAState, coerce_triple


async def window_triples_node(state: ARAState) -> dict[str, Any]:
    """Select the current window (``valid_triples``) vs. previous window."""
    return {}


def _key(triple: Any) -> tuple[str, str, str]:
    t = coerce_triple(triple)
    return (
        t.subject.id or t.subject.name,
        t.predicate,
        t.object.id or t.object.name,
    )


async def detect_changes_node(state: ARAState) -> dict[str, Any]:
    """Detect emerging / fading / relation_shift events between windows."""
    current = state.get("valid_triples", [])
    previous = state.get("prev_valid_triples", [])

    current_set = {_key(t) for t in current}
    previous_set = {_key(t) for t in previous}

    events: list[dict[str, Any]] = []

    for t in current:
        if _key(t) not in previous_set:
            parsed = coerce_triple(t)
            events.append(
                {
                    "window": "current",
                    "entity_id": parsed.subject.id or parsed.subject.name,
                    "change_type": "emerging",
                    "before": "",
                    "after": parsed.predicate,
                    "evidence": [parsed.provenance.model_dump()],
                }
            )

    for t in previous:
        if _key(t) not in current_set:
            parsed = coerce_triple(t)
            events.append(
                {
                    "window": "previous",
                    "entity_id": parsed.subject.id or parsed.subject.name,
                    "change_type": "fading",
                    "before": parsed.predicate,
                    "after": "",
                    "evidence": [parsed.provenance.model_dump()],
                }
            )

    cur_pred = Counter(coerce_triple(t).predicate for t in current)
    prev_pred = Counter(coerce_triple(t).predicate for t in previous)
    all_preds = set(cur_pred) | set(prev_pred)
    for pred in all_preds:
        cur_count = cur_pred.get(pred, 0)
        prev_count = prev_pred.get(pred, 0)
        total = max(cur_count + prev_count, 1)
        diff = abs(cur_count - prev_count) / total
        if diff > 0.5:
            events.append(
                {
                    "window": "current",
                    "entity_id": None,
                    "change_type": "relation_shift",
                    "before": f"prev_count={prev_count}",
                    "after": f"cur_count={cur_count}",
                    "evidence": [],
                }
            )

    state["evolution_events"] = events
    return {"evolution_events": events}


async def summarize_evolution_node(state: ARAState) -> dict[str, Any]:
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
    return {"evolution_report": report}


__all__ = ["window_triples_node", "detect_changes_node", "summarize_evolution_node"]
