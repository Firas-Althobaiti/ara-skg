"""Prompts used by the evolution subgraph."""

SYSTEM_WINDOW_TRIPLES = """
Extract all triples that were added or modified in the given time window.
Return a JSON array of triples (subject, predicate, object, confidence, provenance).
"""

SYSTEM_DETECT_CHANGES = """
Given two sets of triples (current and previous), detect emerging, fading, renamed, and relation_shift events.
Return a JSON array of EvolutionEvent objects (window, entity_id, change_type, before, after, evidence).
"""

SYSTEM_SUMMARIZE_EVOLUTION = """
Generate a markdown report summarizing the evolution events, citing evidence.
Return a single string containing the markdown report.
"""

__all__ = [
    "SYSTEM_WINDOW_TRIPLES",
    "SYSTEM_DETECT_CHANGES",
    "SYSTEM_SUMMARIZE_EVOLUTION",
]
