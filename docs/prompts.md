# Prompt catalog (v1.0.0)

Every prompt shipped in `ara/prompts/*.py`, tagged **v1.0.0**, with a
"when to use" note. All prompts are plain string constants returning strict
JSON from the LLM.

## Extraction — `ara/prompts/extraction.py`

| Prompt | When to use |
|---|---|
| `SYSTEM_EXTRACT_ENTITIES` (v1.0.0) | First pass over a chunk: pull entity mentions (gene/protein/drug/disease/pathway/phenotype/other) with aliases + confidence as JSON |
| `SYSTEM_EXTRACT_RELATIONS` (v1.0.0) | Second pass: extract (subject, predicate, object) triples with confidence and an evidence snippet |
| `SYSTEM_VALIDATE_TRIPLES` (v1.0.0) | Critic pass: drop triples with confidence < 0.7 or missing provenance (paper_id, chunk_id, span, extracted_by) |

## Hypothesis — `ara/prompts/hypothesis.py`

| Prompt | When to use |
|---|---|
| `SYSTEM_GENERATE` (v1.0.0) | Given KG context, produce 3–5 novel testable hypotheses conforming to the `Hypothesis` schema (statement, mechanism, entities, evidence, novelty, plausibility) |
| `SYSTEM_RANK` (v1.0.0) | Sort hypotheses by `novelty_score + plausibility_score` descending |
| `SYSTEM_CRITIQUE` (v1.0.0) | Reject hypotheses with fewer than 2 supporting triples; emit a critique message |

## Query — `ara/prompts/cypher.py`

| Prompt | When to use |
|---|---|
| `SYSTEM_NL2CYPHER` (v1.0.0) | Translate a natural-language question into a **read-only** Cypher pattern + params + rationale |
| `SYSTEM_GUARD_CYPHER` (v1.0.0) | Safety guard: reject any query containing write keywords (CREATE/DELETE/MERGE/SET/WITH) |
| `SYSTEM_RUN_CYPHER` (v1.0.0) | Execute the guarded pattern and return `{result, runtime}` as JSON |
| `SYSTEM_SYNTHESIZE_ANSWER` (v1.0.0) | Combine subgraph context + retrieved chunks + query rows into a concise evidence-backed answer |

## Evolution — `ara/prompts/evolution.py`

| Prompt | When to use |
|---|---|
| `SYSTEM_DETECT_CHANGES` (v1.0.0) | Given previous + current triple sets, emit JSON events: `change_type` (emerging/fading/renamed/relation_shift), entity, before, after, evidence |
| `SYSTEM_SUMMARIZE_EVOLUTION` (v1.0.0) | Turn the event list into a concise markdown evolution report |

!!! note "Versioning"
    Prompts are tagged `v1.0.0`. When a prompt changes, bump its tag and note
    the change in `CHANGELOG.md` — downstream eval runs (Phase 12 gold set)
    depend on stable prompt behavior.
