# ADR-0004 — Human approval before KG writes (`interrupt_before`)

- **Status:** Accepted (v1.0.0)
- **Date:** 2026-11-18

## Context

The graph_update subgraph mutates the knowledge graph (upsert triples, create
entities). In an autonomous research assistant, silent KG writes are risky:
extracted triples can be wrong, and once merged they contaminate downstream
query/hypothesis/evolution results.

## Decision

Compile the main graph with `interrupt_before=["graph_update"]`
(`ara/graphs/main.py`). Execution pauses right before the graph-update
subgraph runs; a human (or an outer orchestrator) inspects the pending
`resolved_triples` in the checkpointed state and resumes by re-invoking with
the same `thread_id`. The subgraph itself also has a `rollback_on_error` node.

## Consequences

- KG writes are never fully automatic: every mutation is reviewable.
- Resume works because of the checkpointer (ADR-0002) — the interrupt is
  durable across process restarts.
- Cost: the fully autonomous `make demo` path invokes the demo graph builder
  without that interrupt (the demo is a sandboxed, offline artifact), while
  the production `app` singleton always interrupts. This split is explicit in
  `scripts/demo.py` vs `ara/graphs/main.py`.

## Alternatives

- **Critic-only gating** (validate then write in the same run) — simpler, but
  a single bad validation pass writes bad data; rejected for a research tool.
- **Confidence threshold auto-approve** — could be added later as an optional
  policy on top of the interrupt.
