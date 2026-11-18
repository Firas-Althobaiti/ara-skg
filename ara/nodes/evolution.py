"""Evolution nodes: window → detect changes → summarize into a report.

Baseline mode: the first evolution run (no previous-window snapshot) does
not report every existing triple as "emerging". Instead it establishes a
baseline — the snapshot is written with a ``__baseline__`` marker and the
run reports zero events with a "baseline established" message. The next
run diffs against that baseline normally.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

from ara.schemas import ARAState, coerce_triple

BASELINE_MARKER = "__baseline__"
BASELINE_MESSAGE = "Baseline established. Re-run after new ingestions to see changes."


def load_prev_snapshot(prev_path: Path) -> tuple[list[Any], bool]:
    """Load the previous-window snapshot from *prev_path*.

    Returns ``(triples, is_baseline_run)``. ``is_baseline_run`` is True when
    no snapshot file exists yet — the caller should treat this run as the
    baseline (0 events) and persist the snapshot with the baseline marker.
    """
    if not prev_path.exists():
        return [], True
    raw = json.loads(prev_path.read_text(encoding="utf-8"))
    return list(raw.get("triples", [])), False


def save_snapshot(prev_path: Path, triples: list[Any], *, baseline: bool) -> None:
    """Atomically persist the current window as the next run's "previous".

    When *baseline* is True the snapshot is written as
    ``{"__baseline__": true, "triples": [...]}``.
    """
    payload: dict[str, Any] = {"triples": triples}
    if baseline:
        payload[BASELINE_MARKER] = True
    prev_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = prev_path.with_suffix(prev_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp_path, prev_path)


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
    """Detect emerging / fading / relation_shift events between windows.

    Baseline run (``state['prev_baseline']`` is True, i.e. no previous
    snapshot existed): report zero events — the current window *is* the
    baseline, not a diff against an empty graph.
    """
    if state.get("prev_baseline"):
        state["evolution_events"] = []
        return {"evolution_events": []}

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
        report = BASELINE_MESSAGE if state.get("prev_baseline") else "No evolution events detected."
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


__all__ = [
    "BASELINE_MARKER",
    "BASELINE_MESSAGE",
    "load_prev_snapshot",
    "save_snapshot",
    "window_triples_node",
    "detect_changes_node",
    "summarize_evolution_node",
]
