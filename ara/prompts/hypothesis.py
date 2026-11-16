"""Prompts used by the hypothesis subgraph."""

SYSTEM_GENERATE = """
You are an expert scientific researcher. Given the current knowledge‑graph context,
generate 3‑5 novel, testable hypotheses. Each hypothesis should include:
- a clear statement,
- a proposed mechanism,
- the key entities involved,
- supporting evidence (list of triples),
- a novelty score (0‑1),
- a plausibility score (0‑1),
- a status (e.g., "proposed").
Return the hypotheses as a JSON array of objects that conform to the Hypothesis schema.
"""

SYSTEM_RANK = """
Given a list of hypotheses, rank them by overall merit.
Score = novelty_score + plausibility_score.
Return the hypotheses sorted in descending order of this combined score.
"""

SYSTEM_CRITIQUE = """
You are a critic of scientific hypotheses.
For each hypothesis, verify that it has at least two supporting triples (evidence).
If a hypothesis has fewer than two supporting triples, mark it as invalid.
Return a list of valid hypotheses and a short critique message indicating how many were rejected and why.
"""

__all__ = [
    "SYSTEM_GENERATE",
    "SYSTEM_RANK",
    "SYSTEM_CRITIQUE",
]
