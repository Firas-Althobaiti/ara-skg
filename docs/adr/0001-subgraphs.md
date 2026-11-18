# ADR-0001 — One subgraph per research phase

- **Status:** Accepted (v1.0.0)
- **Date:** 2026-11-18

## Context

An autonomous research assistant touches very different concerns: fetching
papers, extracting triples, writing to a KG, answering questions, generating
hypotheses, proposing experiments, and tracking evolution. Each concern has its
own state slice, failure modes, and testing strategy. A single flat graph would
mix them all and make routing, retries and interrupts hard to reason about.

## Decision

Structure the application as **one compiled subgraph per research phase**
(ingestion, extraction, graph_update, query, hypothesis, experiment, evolution)
and wire them into a main `StateGraph` with a supervisor node that classifies
the user intent (`state["route"]`) and dispatches to exactly one subgraph.
All subgraphs share the single typed `ARAState` and are registered in
`SUBGRAPHS` in `ara/graphs/main.py`.

## Consequences

- Each subgraph is independently buildable, testable and compilable
  (`build_*_graph()`), which is how the unit/e2e tests exercise them.
- State is explicit: nodes only read/write their own slice of `ARAState`,
  which keeps `mypy --strict` tractable.
- Routing is a single conditional edge, easy to audit and to extend (add a
  key to `SUBGRAPHS` + the supervisor's path map).
- Cost: one extra indirection layer; the critic/replan loop lives at the top
  level so errors from any subgraph funnel through the same recovery path.

## Alternatives

- **Single flat graph with ~25 nodes** — simpler to draw, but routing,
  interrupts and per-phase tests become entangled; rejected.
- **Separate processes/services per phase** — better isolation, but requires
  a message bus and loses LangGraph's checkpoint/resume semantics; rejected
  for v1.
