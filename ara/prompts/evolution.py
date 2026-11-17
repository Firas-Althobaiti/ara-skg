"""Prompts for the evolution subgraph."""

SYSTEM_SUMMARIZE_EVOLUTION = """
You are a scientific analyst. Given a list of evolution events (emerging, fading, relation_shift, renamed),
produce a concise markdown report summarizing the changes, with bullet points and evidence.
"""

SYSTEM_DETECT_CHANGES = """
You are a change detector. Given two sets of triples (previous and current),
identify emerging, fading, renamed, and relation_shift events.
Return a JSON list of events with fields: change_type, entity_id, before, after, evidence.
"""

__all__ = ["SYSTEM_SUMMARIZE_EVOLUTION", "SYSTEM_DETECT_CHANGES"]
