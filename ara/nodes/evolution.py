from typing import Dict, Any, List
from ara.state import ARAState
from ara.schemas import EvolutionEvent
from ara.config import get_settings
import asyncio

# ----------------------------------------------------------------------
# Dummy LLM call – in production this would call the LLM with the appropriate prompt.
# ----------------------------------------------------------------------
class DummyMessage:
    def __init__(self, content: str):
        self.content = content

async def _call_llm(prompt: str) -> str:
    """Mock LLM that returns a short markdown summary."""
    return "## Evolution Summary\n\n- **Emerging**: GeneA → ProteinX\n- **Fading**: ProteinX → KinaseY\n- **Renamed**: GeneB (formerly GeneC)\n- **Relation_shift**: 'binds' → 'phosphorylates'"

async def window_triples_node(state: ARAState) -> Dict[str, Any]:
    """Return all valid triples as the triples for the current window."""
    # In a real system we would filter by timestamp; here we return all valid triples.
    return state

async def detect_changes_node(state: ARAState) -> Dict[str, Any]:
    """Detect emerging, fading, renamed, and relation_shift events."""
    current = state.get("valid_triples", [])
    previous = state.get("prev_valid_triples", [])

    # Convert to sets of (subject_id, predicate, object_id) for set operations.
    def _key(triple):
        return (triple["subject"]["id"], triple["predicate"], triple["object"]["id"])

    current_set = {_key(t) for t in current}
    previous_set = {_key(t) for t in previous}

    emerging = [
        {"window": "current", "entity_id": None, "change_type": "emerging",
         "before": "", "after": "", "evidence": []}
        for t in current if _key(t) not in previous_set
    ]

    fading = [
        {"window": "previous", "entity_id": None, "change_type": "fading",
         "before": "", "after": "", "evidence": []}
        for t in previous if _key(t) not in current_set
    ]

    # Renamed detection – compare (id, name) pairs.
    current_names = {(t["subject"]["id"], t["subject"]["name"]) for t in current}
    previous_names = {(t["subject"]["id"], t["subject"]["name"]) for t in previous}
    renamed = []
    for pid, name in current_names:
        if (pid, name) not in previous_names:
            # find the previous name for this id
            prev_name = next(
                (t["subject"]["name"] for t in previous if t["subject"]["id"] == pid), None
            )
            if prev_name:
                emerging.append({
                    "window": "current",
                    "entity_id": pid,
                    "change_type": "renamed",
                    "before": prev_name,
                    "after": name,
                    "evidence": []
                })

    # Relation shift detection – look for new predicates.
    current_predicates = {t["predicate"] for t in current}
    previous_predicates = {t["predicate"] for t in previous}
    relation_shift = []
    if current_predicates - previous_predicates:
        relation_shift.append({
            "window": "current",
            "entity_id": None,
            "change_type": "relation_shift",
            "before": ", ".join(previous_predicates),
            "after": ", ".join(current_predicates),
            "evidence": []
        })

    events = []
    events.extend(emerging)
    events.extend(fading)
    events.extend(renamed)
    events.extend(relation_shift)

    # Populate evidence placeholders (in a real system we would pull evidence from the graph)
    for ev in events:
        ev["evidence"] = []  # placeholder

    state["evolution_events"] = events
    return state

async def summarize_evolution_node(state: ARAState) -> Dict[str, Any]:
    """Generate a markdown report summarizing the evolution events."""
    events: List[EvolutionEvent] = state.get("evolution_events", [])
    if not events:
        report = "No evolution events detected."
    else:
        lines = ["## Evolution Summary\n\n"]
        for ev in events:
            line = f"- **{ev.change_type}**: {ev.before} → {ev.after}"
            if ev.window:
                line += f" (window: {ev.window})"
            line += f"  \n  Evidence: {', '.join(ev.evidence) or 'none'}"
            lines.append(line)
        report = "\n".join(lines)
    state["evolution_report"] = report
    return state
