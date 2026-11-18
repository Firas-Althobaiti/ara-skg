# ADR-0003 — Chunk fan-out: map-style nodes instead of `Send`

- **Status:** Accepted (v1.0.0)
- **Date:** 2026-11-18

## Context

Extraction must process every chunk of every paper. LangGraph offers `Send`
for dynamic fan-out (one node invocation per item), which is the idiomatic way
to parallelize per-chunk LLM calls.

## Decision

For v1.0.0 the fan-out is **map-style inside a single node**: the extraction
nodes iterate over `state["chunks"]` in a deterministic loop and accumulate
results into `state["extracted_entities"]` / `state["extracted_triples"]`.
The extraction subgraph is a linear chain
(`extract_entities → extract_relations → link_entities → validate_triples`).

## Consequences

- Deterministic, easily testable with the mocked LLM — no concurrency, so
  the test suite is reproducible and fast (61 tests, ~5s).
- Checkpointing stays simple: one checkpoint per subgraph step instead of one
  per fanned-out branch, which keeps the SQLite checkpoint file small and the
  resume logic in ADR-0002 straightforward.
- Cost: no intra-node parallelism. With a real LLM this serializes chunk
  processing.

## Alternatives

- **`Send` fan-out per chunk** — the right choice once a real async LLM is
  wired in (v1.1+): parallel chunk extraction with per-chunk checkpoints.
  Kept as the documented migration path; the state fields
  (`extracted_entities`, `extracted_triples`) are already list-shaped so the
  switch is local to the extraction nodes.
- **External task queue (Celery etc.)** — overkill for a local-first tool.
